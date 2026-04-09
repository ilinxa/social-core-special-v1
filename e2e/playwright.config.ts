import { defineConfig, devices } from '@playwright/test';
import * as dotenv from 'dotenv';
import * as path from 'path';

// Load .env from e2e directory
dotenv.config({ path: path.resolve(__dirname, '.env') });

const BASE_URL = process.env.E2E_BASE_URL ?? 'http://localhost:3001';

/**
 * Playwright configuration for the Social Media Advertising Platform E2E tests.
 *
 * Four projects aligned with the three-layer test architecture:
 *   - smoke-desktop:  L1 smoke tests on desktop viewport (4 workers, fast)
 *   - smoke-mobile:   L1 smoke tests on mobile viewport (2 workers)
 *   - workflows:      L2 cross-system workflow tests (2 workers, video on retry)
 *   - scenarios:       L3 persona scenarios (1 worker, serial, full recording)
 *
 * @see e2e/docs/architecture.md Section 17 — Run Strategy & Time Budgets
 */
export default defineConfig({
  // ---------------------------------------------------------------------------
  // Global Settings
  // ---------------------------------------------------------------------------
  testDir: './tests',
  timeout: 30_000,
  expect: {
    timeout: 10_000,
    toHaveScreenshot: {
      maxDiffPixelRatio: 0.002, // 0.2% threshold for visual regression
    },
  },

  // Fail the build on test.only() in CI
  forbidOnly: !!process.env.CI,

  // Global setup/teardown: DB reset, migrations, seed data, auth states
  globalSetup: require.resolve('./global-setup.ts'),
  globalTeardown: require.resolve('./global-teardown.ts'),

  // Shared reporter configuration
  reporter: process.env.CI
    ? [
        ['html', { outputFolder: 'reports/e2e-html', open: 'never' }],
        ['json', { outputFile: 'reports/e2e-results.json' }],
        ['github'],
      ]
    : [
        ['html', { outputFolder: 'reports/e2e-html', open: 'on-failure' }],
        ['list'],
      ],

  // Output directory for test artifacts (screenshots, videos, traces)
  outputDir: 'test-results',

  // ---------------------------------------------------------------------------
  // Projects
  // ---------------------------------------------------------------------------
  projects: [
    // -------------------------------------------------------------------------
    // L1 Smoke Tests — Desktop (1280x720)
    // -------------------------------------------------------------------------
    {
      name: 'smoke-desktop',
      testDir: './tests/smoke',
      testIgnore: '**/responsive/**',
      use: {
        baseURL: BASE_URL,
        viewport: { width: 1280, height: 720 },
        actionTimeout: 15_000,
        trace: 'on-first-retry',
        screenshot: 'only-on-failure',
      },
      retries: 1, // Backend login can 500 under concurrent load
      fullyParallel: true,
      workers: process.env.CI ? 2 : 4,
    },

    // -------------------------------------------------------------------------
    // L1 Smoke Tests — Mobile (iPhone 14 Pro)
    // -------------------------------------------------------------------------
    {
      name: 'smoke-mobile',
      testDir: './tests/smoke/responsive',
      use: {
        baseURL: BASE_URL,
        ...devices['iPhone 14 Pro'],
        actionTimeout: 15_000,
        trace: 'on-first-retry',
        screenshot: 'only-on-failure',
      },
      retries: 1, // Backend login can 500 under concurrent load
      fullyParallel: true,
      workers: process.env.CI ? 1 : 2,
    },

    // -------------------------------------------------------------------------
    // L2 Workflow Tests (1280x720, video on retry)
    // -------------------------------------------------------------------------
    {
      name: 'workflows',
      testDir: './tests/workflows',
      use: {
        baseURL: BASE_URL,
        viewport: { width: 1280, height: 720 },
        actionTimeout: 15_000,
        trace: 'on-first-retry',
        screenshot: 'only-on-failure',
        video: 'on-first-retry',
      },
      retries: process.env.CI ? 2 : 0,
      fullyParallel: true,
      workers: process.env.CI ? 1 : 2,
    },

    // -------------------------------------------------------------------------
    // L3 Persona Scenarios (1280x720, serial, full recording)
    // -------------------------------------------------------------------------
    {
      name: 'scenarios',
      testDir: './tests/scenarios',
      use: {
        baseURL: BASE_URL,
        viewport: { width: 1280, height: 720 },
        actionTimeout: 15_000,
        trace: 'on',
        screenshot: 'on',
        video: 'on',
      },
      retries: 0, // L3 scenarios must pass on first try — no retries
      fullyParallel: false,
      workers: 1, // Serial execution — each scenario depends on previous steps
    },
  ],

  // ---------------------------------------------------------------------------
  // Web Server (optional — uncomment if E2E stack is managed by Playwright)
  // ---------------------------------------------------------------------------
  // By default, the E2E Docker stack is started externally via `make e2e-up`.
  // Uncomment below to have Playwright manage it:
  //
  // webServer: [
  //   {
  //     command: 'make e2e-up',
  //     url: 'http://localhost:8001/health/',
  //     reuseExistingServer: !process.env.CI,
  //     timeout: 120_000,
  //   },
  // ],
});
