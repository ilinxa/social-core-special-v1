/**
 * HTTP API client for E2E test data setup.
 *
 * Ported from Python `APIHelper` in `backend/tests/api_integration/conftest.py`.
 * Connects directly to backend:8001 (bypasses frontend proxy).
 *
 * Key patterns:
 * - `X-Client-Type: mobile` forces refresh tokens in response body (not HttpOnly)
 * - Always call `clearToken()` before AllowAny endpoints (DRF validates stale tokens)
 * - Bearer token auto-attached after login
 */

import { API_URL, DEFAULT_PASSWORD } from './constants';
import type { AuthTokens, LoginResponse, RegisterResponse } from './types';
import { usernameFromEmail } from './utils';

export class ApiClient {
  private baseUrl: string;
  private token: string | null = null;

  constructor(baseUrl: string = API_URL) {
    this.baseUrl = baseUrl;
  }

  // ---------------------------------------------------------------------------
  // Token Management
  // ---------------------------------------------------------------------------

  setToken(token: string): void {
    this.token = token;
  }

  clearToken(): void {
    this.token = null;
  }

  getToken(): string | null {
    return this.token;
  }

  // ---------------------------------------------------------------------------
  // HTTP Methods
  // ---------------------------------------------------------------------------

  private url(path: string): string {
    const cleanPath = path.startsWith('/') ? path.slice(1) : path;
    const base = this.baseUrl.endsWith('/') ? this.baseUrl : `${this.baseUrl}/`;
    return `${base}${cleanPath}`;
  }

  private headers(): Record<string, string> {
    const h: Record<string, string> = {
      'Content-Type': 'application/json',
      Accept: 'application/json',
      'X-Client-Type': 'mobile', // Forces tokens in response body
    };
    if (this.token) {
      h['Authorization'] = `Bearer ${this.token}`;
    }
    return h;
  }

  async get(path: string): Promise<Response> {
    return fetch(this.url(path), {
      method: 'GET',
      headers: this.headers(),
    });
  }

  async post(path: string, data?: unknown): Promise<Response> {
    return fetch(this.url(path), {
      method: 'POST',
      headers: this.headers(),
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  async patch(path: string, data?: unknown): Promise<Response> {
    return fetch(this.url(path), {
      method: 'PATCH',
      headers: this.headers(),
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  async put(path: string, data?: unknown): Promise<Response> {
    return fetch(this.url(path), {
      method: 'PUT',
      headers: this.headers(),
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  async delete(path: string): Promise<Response> {
    return fetch(this.url(path), {
      method: 'DELETE',
      headers: this.headers(),
    });
  }

  // ---------------------------------------------------------------------------
  // Auth Convenience Methods
  // ---------------------------------------------------------------------------

  /**
   * Register a new user. Clears token first (AllowAny endpoint).
   * Returns parsed response with user and tokens.
   */
  async register(
    email: string,
    password: string = DEFAULT_PASSWORD,
    username?: string,
  ): Promise<RegisterResponse> {
    this.clearToken();
    const uname = username ?? usernameFromEmail(email);
    const res = await this.post('auth/register/', { email, username: uname, password });
    if (!res.ok) {
      const body = await res.text();
      throw new Error(`Register failed (${res.status}): ${body}`);
    }
    const data = (await res.json()) as RegisterResponse;
    this.setToken(data.tokens.access_token);
    return data;
  }

  /**
   * Login a user. Clears token first (AllowAny endpoint).
   * Returns parsed response with user and tokens.
   */
  async login(email: string, password: string = DEFAULT_PASSWORD): Promise<LoginResponse> {
    this.clearToken();
    const res = await this.post('auth/login/', { email, password });
    if (!res.ok) {
      const body = await res.text();
      throw new Error(`Login failed (${res.status}): ${body}`);
    }
    const data = (await res.json()) as LoginResponse;
    this.setToken(data.tokens.access_token);
    return data;
  }

  /**
   * Refresh tokens. Clears token first (AllowAny endpoint).
   */
  async refreshTokens(refreshToken: string): Promise<AuthTokens> {
    this.clearToken();
    const res = await this.post('auth/refresh/', { refresh_token: refreshToken });
    if (!res.ok) {
      const body = await res.text();
      throw new Error(`Refresh failed (${res.status}): ${body}`);
    }
    const data = (await res.json()) as AuthTokens;
    this.setToken(data.access_token);
    return data;
  }

  /**
   * Verify email with 6-digit code.
   */
  async verifyEmail(email: string, code: string): Promise<Response> {
    this.clearToken();
    return this.post('auth/verify-email/', { email, code });
  }

  /**
   * Register + verify email via DB code lookup.
   * Requires a DbClient instance to fetch the verification code.
   */
  async registerAndVerify(
    email: string,
    password: string,
    getCodeFn: (email: string) => Promise<string | null>,
    username?: string,
  ): Promise<RegisterResponse> {
    const registerData = await this.register(email, password, username);
    const code = await getCodeFn(email);
    if (!code) {
      throw new Error(`No verification code found for ${email}`);
    }
    const verifyRes = await this.verifyEmail(email, code);
    if (!verifyRes.ok) {
      const body = await verifyRes.text();
      throw new Error(`Email verification failed (${verifyRes.status}): ${body}`);
    }
    // Re-login to get fresh tokens (verification may change user state)
    return { ...registerData, ...(await this.login(email, password)) };
  }

  // ---------------------------------------------------------------------------
  // Business
  // ---------------------------------------------------------------------------

  async createBusiness(data: {
    legal_name: string;
    country: string;
    slug?: string;
  }): Promise<Response> {
    return this.post('business/', data);
  }

  // ---------------------------------------------------------------------------
  // Transactions
  // ---------------------------------------------------------------------------

  async createInvitation(data: {
    transaction_type: string;
    target_user_id: string;
    context_type: string;
    context_id: string;
    payload?: Record<string, unknown>;
  }): Promise<Response> {
    return this.post('transactions/invitation/', data);
  }

  async acceptTransaction(transactionId: string): Promise<Response> {
    return this.post(`transactions/${transactionId}/accept/`);
  }

  // ---------------------------------------------------------------------------
  // Health Check
  // ---------------------------------------------------------------------------

  async healthCheck(): Promise<boolean> {
    try {
      const res = await fetch(this.baseUrl.replace('/api/v1', '/health/'));
      return res.ok;
    } catch {
      return false;
    }
  }
}
