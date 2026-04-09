/**
 * E2E test constants — URLs, ports, timeouts, credentials.
 *
 * All values are configurable via environment variables (.env file).
 * Defaults target the isolated E2E Docker stack.
 */

// --- Application URLs ---
export const BASE_URL = process.env.E2E_BASE_URL ?? 'http://localhost:3001';
export const API_URL = process.env.E2E_API_URL ?? 'http://localhost:8001/api/v1';
export const WS_URL = process.env.E2E_WS_URL ?? 'ws://localhost:8001/ws';
export const BACKEND_URL = process.env.E2E_BACKEND_URL ?? 'http://localhost:8001';

// --- Database ---
export const DB_CONFIG = {
  host: process.env.E2E_DB_HOST ?? 'localhost',
  port: parseInt(process.env.E2E_DB_PORT ?? '5433', 10),
  database: process.env.E2E_DB_NAME ?? 'backend_core_e2e_db',
  user: process.env.E2E_DB_USER ?? 'django_user',
  password: process.env.E2E_DB_PASSWORD ?? 'django_password',
} as const;

// --- Timeouts ---
export const TIMEOUT = parseInt(process.env.E2E_TIMEOUT ?? '30000', 10);
export const ACTION_TIMEOUT = parseInt(process.env.E2E_ACTION_TIMEOUT ?? '15000', 10);

// --- Test Credentials ---
export const DEFAULT_PASSWORD = process.env.E2E_DEFAULT_PASSWORD ?? 'TestPass123!';

// --- Storage State Paths ---
export const STORAGE_STATES_DIR = 'fixtures/storage-states';
export const STORAGE_STATE = {
  regularUser: `${STORAGE_STATES_DIR}/regular-user.json`,
  businessOwner: `${STORAGE_STATES_DIR}/business-owner.json`,
  businessMember: `${STORAGE_STATES_DIR}/business-member.json`,
  platformAdmin: `${STORAGE_STATES_DIR}/platform-admin.json`,
  unauthenticated: `${STORAGE_STATES_DIR}/unauthenticated.json`,
} as const;

// --- Feature Gate Config ---
export const DEPLOYMENT_CONFIG_PATH =
  process.env.E2E_DEPLOYMENT_CONFIG_PATH ?? '../backend/deployment_config.json';

// --- Pre-built Test Users (created by global-setup) ---
export const TEST_USERS = {
  regular: {
    email: 'e2e-regular@test.com',
    username: 'e2e_regular',
    password: DEFAULT_PASSWORD,
  },
  businessOwner: {
    email: 'e2e-bizowner@test.com',
    username: 'e2e_bizowner',
    password: DEFAULT_PASSWORD,
  },
  businessMember: {
    email: 'e2e-bizmember@test.com',
    username: 'e2e_bizmember',
    password: DEFAULT_PASSWORD,
  },
  platformAdmin: {
    email: 'e2e-platform@test.com',
    username: 'e2e_platform',
    password: DEFAULT_PASSWORD,
  },
  secondUser: {
    email: 'e2e-second@test.com',
    username: 'e2e_second',
    password: DEFAULT_PASSWORD,
  },
} as const;

// --- Pre-built Business (created by global-setup) ---
export const E2E_BUSINESS = {
  slug: 'e2e-test-biz',
  legalName: 'E2E Test Business',
} as const;

// --- Polling ---
export const POLL_RETRIES = 15;
export const POLL_DELAY_MS = 1000;
