/**
 * Direct PostgreSQL client for E2E test operations.
 *
 * Ported from Python `DBHelper` in `backend/tests/api_integration/conftest.py`.
 * Used for operations that can't go through the API:
 * - Fetching email verification codes (async Celery task)
 * - Fetching password reset tokens
 * - Granting permissions directly
 * - Setting business max_members
 */

import { Pool, type PoolConfig } from 'pg';
import { DB_CONFIG, POLL_RETRIES, POLL_DELAY_MS } from './constants';
import { retry, sleep } from './utils';

export class DbClient {
  private pool: Pool;
  private config: PoolConfig;

  constructor(config: PoolConfig = DB_CONFIG) {
    this.config = config;
    this.pool = new Pool({
      ...config,
      max: 5,
      idleTimeoutMillis: 30_000,
      connectionTimeoutMillis: 10_000,
    });
  }

  // ---------------------------------------------------------------------------
  // Core Query Methods
  // ---------------------------------------------------------------------------

  async query<T extends Record<string, unknown> = Record<string, unknown>>(
    sql: string,
    params?: unknown[],
  ): Promise<T[]> {
    const client = await this.pool.connect();
    try {
      const result = await client.query(sql, params);
      return result.rows as T[];
    } finally {
      client.release();
    }
  }

  async queryOne<T extends Record<string, unknown> = Record<string, unknown>>(
    sql: string,
    params?: unknown[],
  ): Promise<T | null> {
    const rows = await this.query<T>(sql, params);
    return rows[0] ?? null;
  }

  async execute(sql: string, params?: unknown[]): Promise<void> {
    const client = await this.pool.connect();
    try {
      await client.query(sql, params);
    } finally {
      client.release();
    }
  }

  // ---------------------------------------------------------------------------
  // Email Verification
  // ---------------------------------------------------------------------------

  /**
   * Get verification code for an email. Polls with retries (async Celery task).
   */
  async getVerificationCode(
    email: string,
    retries = POLL_RETRIES,
    delay = POLL_DELAY_MS,
  ): Promise<string | null> {
    for (let attempt = 1; attempt <= retries; attempt++) {
      const row = await this.queryOne<{ code: string }>(
        `SELECT code FROM auth_verification_tokens
         WHERE email = $1 AND is_used = FALSE
         ORDER BY created_at DESC LIMIT 1`,
        [email],
      );
      if (row) return row.code;
      if (attempt < retries) await sleep(delay);
    }
    return null;
  }

  /**
   * Get verification token (UUID) for magic link flow.
   */
  async getVerificationToken(
    email: string,
    retries = POLL_RETRIES,
    delay = POLL_DELAY_MS,
  ): Promise<string | null> {
    for (let attempt = 1; attempt <= retries; attempt++) {
      const row = await this.queryOne<{ token: string }>(
        `SELECT token FROM auth_verification_tokens
         WHERE email = $1 AND is_used = FALSE
         ORDER BY created_at DESC LIMIT 1`,
        [email],
      );
      if (row) return String(row.token);
      if (attempt < retries) await sleep(delay);
    }
    return null;
  }

  // ---------------------------------------------------------------------------
  // Password Reset
  // ---------------------------------------------------------------------------

  async getPasswordResetToken(
    email: string,
    retries = POLL_RETRIES,
    delay = POLL_DELAY_MS,
  ): Promise<string | null> {
    for (let attempt = 1; attempt <= retries; attempt++) {
      const row = await this.queryOne<{ token: string }>(
        `SELECT t.token FROM auth_password_reset_tokens t
         JOIN users u ON t.user_id = u.id
         WHERE u.email = $1 AND t.is_used = FALSE
         ORDER BY t.created_at DESC LIMIT 1`,
        [email],
      );
      if (row) return String(row.token);
      if (attempt < retries) await sleep(delay);
    }
    return null;
  }

  // ---------------------------------------------------------------------------
  // User Management
  // ---------------------------------------------------------------------------

  async verifyUserDirectly(email: string): Promise<void> {
    await this.execute('UPDATE users SET is_verified = TRUE WHERE email = $1', [email]);
  }

  async isUserVerified(email: string): Promise<boolean> {
    const row = await this.queryOne<{ is_verified: boolean }>(
      'SELECT is_verified FROM users WHERE email = $1',
      [email],
    );
    return row?.is_verified ?? false;
  }

  async getUserId(email: string): Promise<string | null> {
    const row = await this.queryOne<{ id: string }>('SELECT id FROM users WHERE email = $1', [
      email,
    ]);
    return row ? String(row.id) : null;
  }

  async makeSuperuser(email: string): Promise<void> {
    await this.execute(
      'UPDATE users SET is_superuser = TRUE, is_staff = TRUE WHERE email = $1',
      [email],
    );
  }

  async grantBusinessCreation(email: string): Promise<void> {
    const rows = await this.query<{ id: string }>(
      'UPDATE users SET can_create_business = TRUE WHERE email = $1 RETURNING id',
      [email],
    );
    if (rows.length === 0) {
      throw new Error(`grantBusinessCreation: no user found with email "${email}"`);
    }
  }

  async unlockAccount(email: string): Promise<void> {
    await this.execute(
      'UPDATE users SET failed_login_attempts = 0, locked_until = NULL WHERE email = $1',
      [email],
    );
  }

  // ---------------------------------------------------------------------------
  // Business Management
  // ---------------------------------------------------------------------------

  async setBusinessMaxMembers(businessId: string, maxMembers: number): Promise<void> {
    await this.execute('UPDATE business_account SET max_members = $1 WHERE id = $2::uuid', [
      maxMembers,
      businessId,
    ]);
  }

  async setBusinessOpenMemberRequest(businessId: string, open: boolean): Promise<void> {
    await this.execute('UPDATE business_account SET open_member_request = $1 WHERE id = $2::uuid', [
      open,
      businessId,
    ]);
  }

  // ---------------------------------------------------------------------------
  // RBAC
  // ---------------------------------------------------------------------------

  async getBaseMemberRoleId(
    accountType: 'business' | 'platform',
    accountId: string,
  ): Promise<string | null> {
    const row = await this.queryOne<{ id: string }>(
      `SELECT id FROM rbac_role
       WHERE account_type = $1 AND account_id = $2::uuid AND is_deleted = FALSE
       ORDER BY level DESC LIMIT 1`,
      [accountType, accountId],
    );
    return row ? String(row.id) : null;
  }

  // ---------------------------------------------------------------------------
  // Platform Management
  // ---------------------------------------------------------------------------

  /**
   * Create an owner membership for a user on the platform account.
   *
   * The platform configure endpoint creates roles but NOT memberships.
   * Platform console access requires an active platform membership, so we
   * must create it explicitly after configuration.
   *
   * Ported from Python `DBHelper.create_platform_membership()`.
   */
  async createPlatformMembership(email: string): Promise<string | null> {
    const userId = await this.getUserId(email);
    if (!userId) return null;

    // Get platform account ID
    const platform = await this.queryOne<{ id: string }>(
      `SELECT id FROM platform_account WHERE singleton_key = 1`,
    );
    if (!platform) return null;
    const platformId = String(platform.id);

    // Get the owner role (level=0, highest privilege)
    const role = await this.queryOne<{ id: string }>(
      `SELECT id FROM rbac_role
       WHERE account_type = 'platform' AND account_id = $1::uuid
       ORDER BY level ASC LIMIT 1`,
      [platformId],
    );
    if (!role) return null;
    const roleId = String(role.id);

    // Check if membership already exists
    const existing = await this.queryOne<{ id: string }>(
      `SELECT id FROM rbac_membership
       WHERE user_id = $1::uuid AND account_type = 'platform'
         AND account_id = $2::uuid AND is_deleted = FALSE`,
      [userId, platformId],
    );
    if (existing) return String(existing.id);

    // Soft-delete any existing owner membership to avoid unique constraint
    await this.execute(
      `UPDATE rbac_membership SET is_deleted = TRUE, deleted_at = NOW()
       WHERE account_type = 'platform' AND account_id = $1::uuid
         AND is_owner = TRUE AND is_deleted = FALSE`,
      [platformId],
    );

    // Create owner membership
    const membershipId = crypto.randomUUID();
    await this.execute(
      `INSERT INTO rbac_membership
         (id, user_id, account_type, account_id, role_id,
          is_owner, status, joined_at, status_reason,
          created_at, updated_at, is_deleted)
       VALUES ($1::uuid, $2::uuid, 'platform', $3::uuid, $4::uuid,
               TRUE, 'active', NOW(), '',
               NOW(), NOW(), FALSE)`,
      [membershipId, userId, platformId, roleId],
    );
    return membershipId;
  }

  // ---------------------------------------------------------------------------
  // Session Management
  // ---------------------------------------------------------------------------

  async countActiveSessions(email: string): Promise<number> {
    const row = await this.queryOne<{ count: string }>(
      `SELECT COUNT(*) as count FROM auth_device_sessions ds
       JOIN users u ON ds.user_id = u.id
       WHERE u.email = $1 AND ds.is_active = TRUE`,
      [email],
    );
    return parseInt(row?.count ?? '0', 10);
  }

  // ---------------------------------------------------------------------------
  // Database Reset
  // ---------------------------------------------------------------------------

  /**
   * Drop and recreate the E2E database for a completely clean state.
   *
   * Connects to the `postgres` admin database to issue DROP/CREATE, then
   * reconnects the main pool to the fresh database.
   *
   * IMPORTANT: After calling this, you must run `manage.py migrate` inside the
   * backend container to rebuild schema + seed data migrations.
   */
  async resetDatabase(): Promise<void> {
    const dbName = (this.config as Record<string, unknown>).database as string;
    const dbUser = (this.config as Record<string, unknown>).user as string;

    // Close existing pool connections to the target database
    await this.pool.end();

    // Connect to 'postgres' admin database
    const adminPool = new Pool({
      ...this.config,
      database: 'postgres',
      max: 1,
    });

    try {
      // Terminate active connections to the target database
      await adminPool.query(
        `SELECT pg_terminate_backend(pid) FROM pg_stat_activity
         WHERE datname = $1 AND pid <> pg_backend_pid()`,
        [dbName],
      );

      // Drop and recreate
      await adminPool.query(`DROP DATABASE IF EXISTS "${dbName}"`);
      await adminPool.query(`CREATE DATABASE "${dbName}" OWNER "${dbUser}"`);
    } finally {
      await adminPool.end();
    }

    // Reconnect pool to the fresh database
    this.pool = new Pool({
      ...this.config,
      max: 5,
      idleTimeoutMillis: 30_000,
      connectionTimeoutMillis: 10_000,
    });
  }

  // ---------------------------------------------------------------------------
  // Test Data Cleanup
  // ---------------------------------------------------------------------------

  /**
   * Delete test users and all related data.
   * Used by global-setup for clean state.
   */
  async cleanupTestUsers(emailPatterns: string[]): Promise<void> {
    for (const pattern of emailPatterns) {
      const tables = [
        'auth_verification_tokens',
        'auth_password_reset_tokens',
        'auth_device_sessions',
        'auth_refresh_tokens',
      ];
      for (const table of tables) {
        try {
          await this.execute(
            `DELETE FROM ${table} WHERE user_id IN (SELECT id FROM users WHERE email LIKE $1)`,
            [pattern],
          );
        } catch {
          // Table may not exist or FK issues — safe to ignore
        }
      }
      try {
        await this.execute(
          `DELETE FROM rbac_membership WHERE user_id IN (SELECT id FROM users WHERE email LIKE $1)`,
          [pattern],
        );
      } catch {
        // Safe to ignore
      }
      try {
        await this.execute('DELETE FROM users WHERE email LIKE $1', [pattern]);
      } catch {
        // Safe to ignore
      }
    }
  }

  // ---------------------------------------------------------------------------
  // Connection Management
  // ---------------------------------------------------------------------------

  async ping(): Promise<boolean> {
    try {
      await this.query('SELECT 1');
      return true;
    } catch {
      return false;
    }
  }

  async close(): Promise<void> {
    await this.pool.end();
  }
}
