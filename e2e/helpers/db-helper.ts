import pg from "pg";
import { PG_CONFIG, POLL_RETRIES, POLL_DELAY_MS } from "./constants";

const { Pool } = pg;

// =============================================================================
// DB HELPER — Direct PostgreSQL access for E2E tests
// =============================================================================
// Mirrors backend/tests/api_integration/conftest.py DBHelper exactly.

let pool: pg.Pool | null = null;

export function getPool(): pg.Pool {
  if (!pool) {
    pool = new Pool(PG_CONFIG);
  }
  return pool;
}

export async function closePool(): Promise<void> {
  if (pool) {
    await pool.end();
    pool = null;
  }
}

// ---------------------------------------------------------------------------
// Generic query helpers
// ---------------------------------------------------------------------------

async function queryOne<T = Record<string, unknown>>(
  sql: string,
  params?: unknown[]
): Promise<T | null> {
  const { rows } = await getPool().query(sql, params);
  return (rows[0] as T) ?? null;
}

async function queryMany<T = Record<string, unknown>>(
  sql: string,
  params?: unknown[]
): Promise<T[]> {
  const { rows } = await getPool().query(sql, params);
  return rows as T[];
}

async function execute(sql: string, params?: unknown[]): Promise<void> {
  await getPool().query(sql, params);
}

// ---------------------------------------------------------------------------
// Polling helper (for async email/celery tasks)
// ---------------------------------------------------------------------------

async function poll<T>(
  fn: () => Promise<T | null>,
  retries = POLL_RETRIES,
  delayMs = POLL_DELAY_MS
): Promise<T | null> {
  for (let i = 0; i < retries; i++) {
    const result = await fn();
    if (result !== null) return result;
    await new Promise((r) => setTimeout(r, delayMs));
  }
  return null;
}

// ---------------------------------------------------------------------------
// Verification codes & tokens
// ---------------------------------------------------------------------------

export async function getVerificationCode(
  email: string,
  retries = POLL_RETRIES
): Promise<string | null> {
  return poll(async () => {
    const row = await queryOne<{ code: string }>(
      `SELECT code FROM auth_verification_tokens
       WHERE email = $1 AND is_used = FALSE
       ORDER BY created_at DESC LIMIT 1`,
      [email]
    );
    return row?.code ?? null;
  }, retries);
}

export async function getPasswordResetToken(
  email: string,
  retries = POLL_RETRIES
): Promise<string | null> {
  return poll(async () => {
    const row = await queryOne<{ token: string }>(
      `SELECT token FROM auth_password_reset_tokens
       WHERE email = $1 AND is_used = FALSE
       ORDER BY created_at DESC LIMIT 1`,
      [email]
    );
    return row?.token ?? null;
  }, retries);
}

// ---------------------------------------------------------------------------
// User operations
// ---------------------------------------------------------------------------

export async function getUserId(email: string): Promise<string | null> {
  const row = await queryOne<{ id: string }>(
    "SELECT id FROM users WHERE email = $1",
    [email]
  );
  return row?.id ?? null;
}

export async function verifyUserDirectly(email: string): Promise<void> {
  await execute("UPDATE users SET is_verified = TRUE WHERE email = $1", [
    email,
  ]);
}

export async function isUserVerified(email: string): Promise<boolean> {
  const row = await queryOne<{ is_verified: boolean }>(
    "SELECT is_verified FROM users WHERE email = $1",
    [email]
  );
  return row?.is_verified ?? false;
}

export async function countActiveSessions(email: string): Promise<number> {
  const row = await queryOne<{ count: string }>(
    `SELECT COUNT(*) as count FROM auth_device_sessions ds
     JOIN users u ON ds.user_id = u.id
     WHERE u.email = $1 AND ds.is_active = TRUE`,
    [email]
  );
  return parseInt(row?.count ?? "0", 10);
}

export async function grantBusinessCreation(email: string): Promise<void> {
  await execute(
    "UPDATE users SET can_create_business = TRUE WHERE email = $1",
    [email]
  );
}

export async function setBusinessMaxMembers(
  businessId: string,
  maxMembers: number
): Promise<void> {
  await execute(
    "UPDATE organization_business_accounts SET max_members = $1 WHERE id = $2",
    [maxMembers, businessId]
  );
}

// ---------------------------------------------------------------------------
// Cleanup — delete test users and related data
// ---------------------------------------------------------------------------

export async function cleanupTestUser(email: string): Promise<void> {
  const userId = await getUserId(email);
  if (!userId) return;

  // Delete in dependency order
  await execute(
    "DELETE FROM auth_verification_tokens WHERE email = $1",
    [email]
  );
  await execute(
    "DELETE FROM auth_password_reset_tokens WHERE email = $1",
    [email]
  );
  await execute(
    "DELETE FROM auth_refresh_tokens WHERE user_id = $1",
    [userId]
  );
  await execute(
    "DELETE FROM auth_device_sessions WHERE user_id = $1",
    [userId]
  );

  // Delete memberships (cascade handles role assignments)
  await execute(
    "DELETE FROM rbac_memberships WHERE user_id = $1",
    [userId]
  );

  // Delete transactions referencing this user
  await execute(
    "DELETE FROM transaction_transactions WHERE initiator_id = $1 OR target_user_id = $1",
    [userId]
  );

  // Delete audit logs
  await execute("DELETE FROM core_audit_logs WHERE actor_id = $1", [userId]);

  // Delete user profile
  await execute("DELETE FROM users_user_profiles WHERE user_id = $1", [userId]);

  // Finally delete user
  await execute("DELETE FROM users WHERE id = $1", [userId]);
}

export async function cleanupTestBusiness(slug: string): Promise<void> {
  const row = await queryOne<{ id: string }>(
    "SELECT id FROM organization_business_accounts WHERE slug = $1",
    [slug]
  );
  if (!row) return;

  const bizId = row.id;

  // Delete business profile
  await execute(
    "DELETE FROM organization_business_profiles WHERE account_id = $1",
    [bizId]
  );

  // Delete RBAC roles and memberships
  await execute(
    "DELETE FROM rbac_memberships WHERE account_type = 'business' AND account_id = $1",
    [bizId]
  );
  await execute(
    "DELETE FROM rbac_roles WHERE account_type = 'business' AND account_id = $1",
    [bizId]
  );

  // Delete transactions referencing this business
  await execute(
    "DELETE FROM transaction_transactions WHERE context_type = 'business' AND context_id = $1",
    [bizId]
  );

  // Delete form mappings
  await execute(
    "DELETE FROM transaction_form_mappings WHERE context_type = 'business' AND context_id = $1",
    [bizId]
  );

  // Delete business account
  await execute(
    "DELETE FROM organization_business_accounts WHERE id = $1",
    [bizId]
  );
}

export async function cleanupAllTestData(): Promise<void> {
  // Find all e2e_ prefixed users
  const users = await queryMany<{ email: string }>(
    "SELECT email FROM users WHERE email LIKE 'e2e_%'"
  );
  for (const u of users) {
    await cleanupTestUser(u.email);
  }

  // Find all e2e- prefixed businesses
  const businesses = await queryMany<{ slug: string }>(
    "SELECT slug FROM organization_business_accounts WHERE slug LIKE 'e2e-%'"
  );
  for (const b of businesses) {
    await cleanupTestBusiness(b.slug);
  }
}
