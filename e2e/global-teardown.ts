import { FullConfig } from "@playwright/test";
import { closePool } from "./helpers/db-helper";

// =============================================================================
// GLOBAL TEARDOWN — Clean up connections after all E2E tests
// =============================================================================

export default async function globalTeardown(_config: FullConfig) {
  console.log("\n[global-teardown] Closing database connections...");
  await closePool();
  console.log("[global-teardown] Done.\n");
}
