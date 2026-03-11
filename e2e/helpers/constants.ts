// =============================================================================
// E2E TEST CONSTANTS
// =============================================================================

export const BASE_URL = "http://localhost:3000";
export const API_BASE_URL = "http://localhost:8000/api/v1";

// PostgreSQL connection (mirrors backend DBHelper)
export const PG_CONFIG = {
  host: "localhost",
  port: 5432,
  database: "backend_core_db",
  user: "django_user",
  password: "postgres_dev_password",
};

// Test users — all prefixed with e2e_ for cleanup isolation
export const TEST_USERS = {
  // User A: Main test user — created by registration tests (U-01..U-07)
  userA: {
    email: "e2e_user_a@test.com",
    username: "e2e_user_a",
    password: "TestPass123!",
    firstName: "Alice",
    lastName: "Tester",
  },
  // User B: Public profile, business owner — pre-seeded in global setup
  userB: {
    email: "e2e_user_b@test.com",
    username: "e2e_user_b",
    password: "TestPass123!",
    firstName: "Bob",
    lastName: "Tester",
  },
  // User C: Private profile — pre-seeded in global setup
  userC: {
    email: "e2e_user_c@test.com",
    username: "e2e_user_c",
    password: "TestPass123!",
    firstName: "Carol",
    lastName: "Private",
  },
  // Deactivation user: Consumed by U-97..U-99 — pre-seeded in global setup
  deactivate: {
    email: "e2e_deactivate@test.com",
    username: "e2e_deactivate",
    password: "TestPass123!",
  },
  // Fresh registration user: Created during registration tests
  fresh: {
    email: "e2e_fresh_reg@test.com",
    username: "e2e_fresh_reg",
    password: "TestPass123!",
  },
  // Taken user: Pre-seeded to test duplicate detection
  taken: {
    email: "e2e_taken_test@test.com",
    username: "e2e_taken_user",
    password: "TestPass123!",
  },
} as const;

// Business pre-seeded in global setup (owned by User B)
export const TEST_BUSINESS = {
  name: "E2E Test Business",
  slug: "e2e-test-business",
};

// Headers required for auth API calls
export const API_HEADERS = {
  "Content-Type": "application/json",
  "X-Client-Type": "mobile",
};

// Timeouts
export const POLL_RETRIES = 15;
export const POLL_DELAY_MS = 1000;
