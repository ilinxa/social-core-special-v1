import { API_BASE_URL, API_HEADERS } from "./constants";

// =============================================================================
// API HELPER — HTTP client for test setup (not browser-based)
// =============================================================================
// Lightweight fetch wrapper for seeding test data outside the browser.

interface AuthResponse {
  access_token: string;
  refresh_token: string;
  email?: string;
  username?: string;
  id?: string;
}

interface RegisterResponse {
  id: string;
  email: string;
  username: string;
}

export async function register(
  email: string,
  password: string,
  username: string
): Promise<RegisterResponse> {
  const resp = await fetch(`${API_BASE_URL}/auth/register/`, {
    method: "POST",
    headers: API_HEADERS,
    body: JSON.stringify({
      email,
      password,
      confirm_password: password,
      username,
    }),
  });

  if (!resp.ok) {
    const body = await resp.text();
    throw new Error(`Register failed (${resp.status}): ${body}`);
  }

  return resp.json();
}

export async function login(
  email: string,
  password: string
): Promise<AuthResponse> {
  const resp = await fetch(`${API_BASE_URL}/auth/login/`, {
    method: "POST",
    headers: API_HEADERS,
    body: JSON.stringify({
      email,
      password,
      device_id: `e2e-${Date.now()}`,
      device_type: "web",
      device_name: "E2E Playwright",
    }),
  });

  if (!resp.ok) {
    const body = await resp.text();
    throw new Error(`Login failed (${resp.status}): ${body}`);
  }

  return resp.json();
}

export async function verifyEmail(
  email: string,
  code: string
): Promise<void> {
  const resp = await fetch(`${API_BASE_URL}/auth/verify-email/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, code }),
  });

  if (!resp.ok) {
    const body = await resp.text();
    throw new Error(`Verify email failed (${resp.status}): ${body}`);
  }
}

export async function updateProfile(
  token: string,
  data: Record<string, unknown>
): Promise<void> {
  const resp = await fetch(`${API_BASE_URL}/users/me/profile/`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(data),
  });

  if (!resp.ok) {
    const body = await resp.text();
    throw new Error(`Update profile failed (${resp.status}): ${body}`);
  }
}

export async function createBusiness(
  token: string,
  data: { name: string; slug: string; description?: string }
): Promise<{ id: string; slug: string }> {
  const resp = await fetch(`${API_BASE_URL}/business/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(data),
  });

  if (!resp.ok) {
    const body = await resp.text();
    throw new Error(`Create business failed (${resp.status}): ${body}`);
  }

  return resp.json();
}

export async function updateBusinessProfile(
  token: string,
  slug: string,
  data: Record<string, unknown>
): Promise<void> {
  const resp = await fetch(`${API_BASE_URL}/business/${slug}/profile/`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(data),
  });

  if (!resp.ok) {
    const body = await resp.text();
    throw new Error(`Update business profile failed (${resp.status}): ${body}`);
  }
}

export async function updateBusinessAccount(
  token: string,
  slug: string,
  data: Record<string, unknown>
): Promise<void> {
  const resp = await fetch(`${API_BASE_URL}/business/${slug}/`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(data),
  });

  if (!resp.ok) {
    const body = await resp.text();
    throw new Error(`Update business account failed (${resp.status}): ${body}`);
  }
}

/**
 * Register a user and verify them via DB, returning their login tokens.
 */
export async function registerAndVerify(
  email: string,
  password: string,
  username: string,
  getVerificationCode: (email: string) => Promise<string | null>
): Promise<AuthResponse> {
  await register(email, password, username);

  const code = await getVerificationCode(email);
  if (!code) {
    throw new Error(`No verification code found for ${email}`);
  }

  await verifyEmail(email, code);
  return login(email, password);
}
