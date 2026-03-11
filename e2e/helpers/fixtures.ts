import { test as base } from "@playwright/test";
import * as db from "./db-helper";

// =============================================================================
// EXTENDED PLAYWRIGHT FIXTURES
// =============================================================================
// Provides db helper as a fixture available to all tests.

type E2EFixtures = {
  db: typeof db;
};

export const test = base.extend<E2EFixtures>({
  db: async ({}, use) => {
    await use(db);
  },
});

export { expect } from "@playwright/test";
