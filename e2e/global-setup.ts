import { FullConfig } from "@playwright/test";
import * as db from "./helpers/db-helper";
import * as api from "./helpers/api-helper";
import { TEST_USERS, TEST_BUSINESS } from "./helpers/constants";

// =============================================================================
// GLOBAL SETUP — Seed test data before all E2E tests
// =============================================================================

export default async function globalSetup(_config: FullConfig) {
  console.log("\n[global-setup] Starting E2E test data seeding...\n");

  // 1. Clean up leftover e2e_ test data from previous runs
  console.log("[global-setup] Cleaning up previous test data...");
  await db.cleanupAllTestData();

  // 2. Register + verify User B (public profile, business owner)
  console.log("[global-setup] Creating User B (public profile)...");
  const userBAuth = await api.registerAndVerify(
    TEST_USERS.userB.email,
    TEST_USERS.userB.password,
    TEST_USERS.userB.username,
    db.getVerificationCode
  );

  // Set User B profile: public, with name/country/city
  await api.updateProfile(userBAuth.access_token, {
    first_name: TEST_USERS.userB.firstName,
    last_name: TEST_USERS.userB.lastName,
    is_public: true,
    country: "US",
    city: "New York",
    bio: "E2E test user with public profile",
    tags: ["e2e", "testing"],
  });

  // 3. Register + verify User C (private profile)
  console.log("[global-setup] Creating User C (private profile)...");
  const userCAuth = await api.registerAndVerify(
    TEST_USERS.userC.email,
    TEST_USERS.userC.password,
    TEST_USERS.userC.username,
    db.getVerificationCode
  );

  await api.updateProfile(userCAuth.access_token, {
    first_name: TEST_USERS.userC.firstName,
    last_name: TEST_USERS.userC.lastName,
    is_public: false,
  });

  // 4. Register + verify "taken" user (for duplicate detection tests)
  console.log("[global-setup] Creating taken user...");
  await api.registerAndVerify(
    TEST_USERS.taken.email,
    TEST_USERS.taken.password,
    TEST_USERS.taken.username,
    db.getVerificationCode
  );

  // 5. Register + verify deactivation user
  console.log("[global-setup] Creating deactivation user...");
  await api.registerAndVerify(
    TEST_USERS.deactivate.email,
    TEST_USERS.deactivate.password,
    TEST_USERS.deactivate.username,
    db.getVerificationCode
  );

  // 6. Grant User B business creation + create test business
  console.log("[global-setup] Creating test business (owned by User B)...");
  await db.grantBusinessCreation(TEST_USERS.userB.email);

  // Re-login User B to get updated permissions
  const userBAuth2 = await api.login(
    TEST_USERS.userB.email,
    TEST_USERS.userB.password
  );

  const business = await api.createBusiness(userBAuth2.access_token, {
    name: TEST_BUSINESS.name,
    slug: TEST_BUSINESS.slug,
    description: "E2E test business account",
  });

  // Set business to public + open member requests + higher member limit
  await api.updateBusinessAccount(userBAuth2.access_token, TEST_BUSINESS.slug, {
    open_member_request: true,
  });

  await db.setBusinessMaxMembers(business.id, 10);

  console.log(
    `[global-setup] Business created: ${TEST_BUSINESS.slug} (id: ${business.id})`
  );

  // NOTE: User A is NOT pre-seeded — registration tests (U-01..U-07) create them.
  // The fresh registration user is also created during tests.

  console.log("\n[global-setup] Test data seeding complete!\n");
  console.log("  Users: B (public), C (private), taken, deactivate");
  console.log(`  Business: ${TEST_BUSINESS.slug} (User B owner)`);
  console.log("  User A: will be created by registration tests\n");
}
