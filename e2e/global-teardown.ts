import type { FullConfig } from '@playwright/test';

/**
 * Global teardown — runs once after all tests.
 *
 * Steps:
 *   1. Log completion summary
 *   2. Note: DB connections are managed per-fixture (auto-closed)
 *   3. Note: Docker stack is managed externally via `make e2e-down`
 */
async function globalTeardown(_config: FullConfig): Promise<void> {
  console.log('=== E2E Global Teardown ===');
  console.log('  Tests complete. Docker stack remains running.');
  console.log('  Run `make e2e-down` to stop the E2E stack.');
  console.log('=== Teardown Done ===');
}

export default globalTeardown;
