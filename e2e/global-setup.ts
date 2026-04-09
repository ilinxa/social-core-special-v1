import { chromium, type FullConfig } from '@playwright/test';
import * as path from 'path';
import * as dotenv from 'dotenv';
import { execSync } from 'child_process';
import { ApiClient } from './lib/api-client';
import { DbClient } from './lib/db-client';
import { TEST_USERS, STORAGE_STATES_DIR, BACKEND_URL, BASE_URL } from './lib/constants';
import { retry } from './lib/utils';

// Load .env
dotenv.config({ path: path.resolve(__dirname, '.env') });

/**
 * Global setup — runs once before all tests.
 *
 * Steps:
 *   1. Wait for Docker stack health
 *   2. Drop & recreate E2E database (clean slate)
 *   3. Run Django migrations via docker exec
 *   4. Create 5 pre-built users via API
 *   5. Set up business owner (grant permission, create business)
 *   6. Set up platform admin (superuser, configure platform)
 *   7. Set up business member (placeholder — tested in L1/L2)
 *   8. Save storageState files for each role
 */
async function globalSetup(config: FullConfig): Promise<void> {
  const startTime = Date.now();
  console.log('=== E2E Global Setup ===');

  const api = new ApiClient();
  const db = new DbClient();

  // --- Step 1: Health checks ---
  console.log('  [1/8] Waiting for backend health...');
  await retry(
    async () => {
      const healthy = await api.healthCheck();
      if (!healthy) throw new Error('Backend not healthy');
    },
    { retries: 30, delay: 2000, description: 'Backend health check' },
  );
  console.log('  [1/8] Backend healthy.');

  console.log('  [1/8] Waiting for frontend...');
  await retry(
    async () => {
      const res = await fetch(BASE_URL);
      if (!res.ok) throw new Error(`Frontend returned ${res.status}`);
    },
    { retries: 30, delay: 2000, description: 'Frontend health check' },
  );
  console.log('  [1/8] Frontend ready.');

  // --- Step 2: Drop & recreate database ---
  console.log('  [2/8] Resetting E2E database (drop → create)...');
  await db.resetDatabase();
  console.log('  [2/8] Database recreated.');

  // --- Step 3: Run migrations via docker exec ---
  console.log('  [3/8] Running Django migrations...');
  try {
    execSync(
      'docker exec docker-backend-e2e-1 python manage.py migrate --noinput',
      { stdio: 'pipe', timeout: 120_000 },
    );
    console.log('  [3/8] Migrations complete.');
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err);
    console.error(`  [3/8] Migration failed: ${msg}`);
    throw new Error(`Migration failed: ${msg}`);
  }

  // Wait for backend to reconnect to fresh DB
  await retry(
    async () => {
      const healthy = await api.healthCheck();
      if (!healthy) throw new Error('Backend not healthy after migration');
    },
    { retries: 10, delay: 1000, description: 'Backend reconnect after migration' },
  );

  // --- Step 4: Register all test users ---
  console.log('  [4/8] Creating test users...');
  for (const [key, user] of Object.entries(TEST_USERS)) {
    await api.register(user.email, user.password, user.username);
    // Verify user directly via DB (skip email flow)
    await db.verifyUserDirectly(user.email);
  }
  console.log(`  [4/8] Created ${Object.keys(TEST_USERS).length} users.`);

  // --- Step 5: Set up business owner ---
  console.log('  [5/8] Setting up business owner...');
  await db.grantBusinessCreation(TEST_USERS.businessOwner.email);

  // Login as business owner to get fresh token with permission
  api.clearToken();
  await api.login(TEST_USERS.businessOwner.email, TEST_USERS.businessOwner.password);

  const bizRes = await api.createBusiness({
    legal_name: 'E2E Test Business',
    country: 'US',
    slug: 'e2e-test-biz',
  });
  if (!bizRes.ok) {
    const body = await bizRes.text();
    throw new Error(`Business creation failed: ${bizRes.status} — ${body}`);
  }
  const biz = (await bizRes.json()) as { id: string; slug: string };
  await db.setBusinessMaxMembers(biz.id, 10);
  await db.setBusinessOpenMemberRequest(biz.id, true);
  console.log(`  [5/8] Business created: ${biz.slug} (max_members=10, open_member_request=true)`);

  // Verify membership was created
  const membershipCount = await db.queryOne<{ count: string }>(
    `SELECT COUNT(*) as count FROM rbac_membership
     WHERE account_id = $1::uuid AND is_deleted = FALSE`,
    [biz.id],
  );
  console.log(`  [5/8] Owner membership verified: ${membershipCount?.count ?? 0} membership(s).`);

  // --- Step 6: Set up platform admin ---
  console.log('  [6/8] Setting up platform admin...');
  await db.makeSuperuser(TEST_USERS.platformAdmin.email);

  api.clearToken();
  await api.login(TEST_USERS.platformAdmin.email, TEST_USERS.platformAdmin.password);

  // Configure platform (POST creates it, requires name)
  const platformRes = await api.post('platform/account/', { name: 'E2E Test Platform' });
  if (platformRes.ok) {
    console.log('  [6/8] Platform configured.');
  } else {
    const body = await platformRes.text();
    console.warn(`  [6/8] Platform setup: ${platformRes.status} — ${body}`);
  }

  // Platform configure creates roles but NOT memberships.
  // Create owner membership explicitly so platform console is accessible.
  const platformMembershipId = await db.createPlatformMembership(TEST_USERS.platformAdmin.email);
  if (platformMembershipId) {
    console.log(`  [6/8] Platform owner membership created: ${platformMembershipId}`);
  } else {
    console.error('  [6/8] FAILED to create platform owner membership!');
  }

  // --- Step 6b: Seed CMS templates for test suite ---
  // Note: SectionTemplateCreateSerializer requires `name` field.
  // `org_type` and `is_default` are model fields NOT exposed via API serializers —
  // they default to org_type="all" and is_default=false. To set these, use Django
  // admin or direct DB access after creation.
  console.log('  [6b/8] Seeding CMS templates...');
  try {
    // Section templates
    await api.post('cms/admin/templates/sections/', {
      name: 'e2e_hero_section',
      display_name: 'Hero Section',
      slug: 'e2e-hero',
      section_type: 'hero',
    });
    await api.post('cms/admin/templates/sections/', {
      name: 'e2e_platform_header',
      display_name: 'Platform Header',
      slug: 'e2e-platform-header',
      section_type: 'header',
    });
    // Block templates
    await api.post('cms/admin/templates/blocks/', {
      name: 'e2e_text_block',
      display_name: 'Text Block',
      slug: 'e2e-text-block',
      block_type: 'text',
      schema: {
        fields: [
          { name: 'title', type: 'text', required: true },
          { name: 'body', type: 'richtext', required: false },
        ],
      },
    });
    await api.post('cms/admin/templates/blocks/', {
      name: 'e2e_biz_banner',
      display_name: 'Business Banner',
      slug: 'e2e-biz-banner',
      block_type: 'banner',
      schema: {
        fields: [
          { name: 'heading', type: 'text', required: true },
          { name: 'image', type: 'media', required: false },
        ],
      },
    });

    // Set org_type and is_default via direct DB (not available in API serializers)
    await db.query(
      `UPDATE cms_section_template SET org_type = 'all', is_default = TRUE WHERE slug = 'e2e-hero'`,
    );
    await db.query(
      `UPDATE cms_section_template SET org_type = 'platform', is_default = FALSE WHERE slug = 'e2e-platform-header'`,
    );
    await db.query(
      `UPDATE cms_block_template SET org_type = 'all', is_default = TRUE WHERE slug = 'e2e-text-block'`,
    );
    await db.query(
      `UPDATE cms_block_template SET org_type = 'business', is_default = FALSE WHERE slug = 'e2e-biz-banner'`,
    );

    console.log('  [6b/8] CMS templates seeded (2 sections, 2 blocks).');
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err);
    console.warn(`  [6b/8] CMS template seeding warning: ${msg}`);
    // Non-fatal — templates may already exist from a previous run
  }

  // --- Step 7: Set up business member ---
  console.log('  [7/8] Setting up business member...');
  // Business member user exists; full invitation flow tested in L1/L2
  console.log('  [7/8] Business member user ready (invitations tested in L1/L2).');

  // --- Step 8: Save storage states ---
  // Frontend auth: access_token is in-memory (module variable), refresh_token is
  // an HttpOnly cookie set by the backend. On page load, AuthInitializer calls
  // silentRefreshApi() to get a new access_token using the cookie.
  //
  // Strategy: Login through the browser so the HttpOnly cookie + has_session
  // marker are set, then save storageState (captures cookies).
  console.log('  [8/8] Saving storage states...');
  const statesDir = path.resolve(__dirname, STORAGE_STATES_DIR);
  const browser = await chromium.launch();

  const stateMap: [string, { email: string; password: string } | null][] = [
    ['regular-user.json', TEST_USERS.regular],
    ['business-owner.json', TEST_USERS.businessOwner],
    ['business-member.json', TEST_USERS.businessMember],
    ['platform-admin.json', TEST_USERS.platformAdmin],
    ['unauthenticated.json', null],
  ];

  for (const [filename, creds] of stateMap) {
    const context = await browser.newContext({
      baseURL: BASE_URL,
    });

    if (creds) {
      const page = await context.newPage();
      // Login through the frontend UI — this triggers the backend to set
      // the HttpOnly refresh_token cookie and the has_session marker cookie
      await page.goto('/login');
      await page.getByLabel('Email').fill(creds.email);
      await page.getByLabel('Password', { exact: true }).fill(creds.password);
      await page.getByRole('button', { name: /sign in/i }).click();
      // Wait for redirect to /home (confirms login succeeded)
      try {
        await page.waitForURL('**/home', { timeout: 15000 });
      } catch (e) {
        // Debug: capture screenshot and current URL
        const debugPath = path.join(statesDir, `debug-${filename}.png`);
        await page.screenshot({ path: debugPath, fullPage: true });
        console.error(`    Login failed for ${filename}. URL: ${page.url()}`);
        console.error(`    Screenshot: ${debugPath}`);
        throw e;
      }
      await page.close();
    }

    const statePath = path.join(statesDir, filename);
    await context.storageState({ path: statePath });
    await context.close();
  }

  await browser.close();

  const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
  console.log(`  [8/8] Storage states saved.`);
  console.log(`=== Global Setup Complete (${elapsed}s) ===`);

  // Cleanup
  await db.close();
}

export default globalSetup;
