/**
 * Test annotation utilities for the coverage reporting system.
 *
 * Centralizes all shared constants, normalization maps, and annotation
 * parsing used by both generate-coverage-matrix.ts and generate-gap-report.ts.
 *
 * @see e2e/docs/architecture.md Section 6 — E2E Parameter Framework (P1-P14)
 * @see e2e/docs/architecture.md Section 16 — Reporting & Coverage
 */

import * as fs from 'fs';
import * as path from 'path';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface TestAnnotations {
  filePath: string;
  layer: string;
  systems: string[];
  parameters: string[];
  priority: string;
  testCount: number;
}

// --- Layers ---
export const Layer = {
  L1: 'L1',
  L2: 'L2',
  L3: 'L3',
} as const;

export type LayerType = (typeof Layer)[keyof typeof Layer];

// --- Systems (annotation values — lowercase for use in @system tags) ---
export const System = {
  AUTH: 'auth',
  USERS: 'users',
  BUSINESS: 'business',
  PLATFORM: 'platform',
  CHAT: 'chat',
  NETWORK: 'network',
  TRANSACTIONS: 'transactions',
  FORMS: 'forms',
  CMS: 'cms',
  NOTIFICATIONS: 'notifications',
  EXPLORE: 'explore',
  FEATURE_GATES: 'feature-gates',
  VISIBILITY: 'visibility',
  LIMITS: 'limits',
  NAVIGATION: 'navigation',
  PUBLIC: 'public',
} as const;

export type SystemType = (typeof System)[keyof typeof System];

// --- Parameters (P1-P14) ---
export const Parameter = {
  P1: 'P1',
  P2: 'P2',
  P3: 'P3',
  P4: 'P4',
  P5: 'P5',
  P6: 'P6',
  P7: 'P7',
  P8: 'P8',
  P9: 'P9',
  P10: 'P10',
  P11: 'P11',
  P12: 'P12',
  P13: 'P13',
  P14: 'P14',
} as const;

export type ParameterType = (typeof Parameter)[keyof typeof Parameter];

// --- Priority ---
export const Priority = {
  P0: 'P0',
  P1: 'P1',
  P2: 'P2',
} as const;

export type PriorityType = (typeof Priority)[keyof typeof Priority];

// ---------------------------------------------------------------------------
// Normalization — maps annotation values to canonical display names
// ---------------------------------------------------------------------------

/**
 * Maps raw @system annotation values (lowercased) to canonical display names.
 * Handles aliases: 'user' → 'Users', 'email' → 'Auth'.
 */
export const SYSTEM_NORMALIZE: Record<string, string> = {
  'auth': 'Auth',
  'users': 'Users',
  'user': 'Users',
  'business': 'Business',
  'platform': 'Platform',
  'chat': 'Chat',
  'network': 'Network',
  'transactions': 'Transactions',
  'forms': 'Forms',
  'cms': 'CMS',
  'notifications': 'Notifications',
  'explore': 'Explore',
  'feature-gates': 'Feature Gates',
  'visibility': 'Visibility',
  'limits': 'Limits',
  'navigation': 'Navigation',
  'public': 'Public',
  'email': 'Auth',
};

/** The 16 canonical systems in display order. */
export const CANONICAL_SYSTEMS = [
  'Auth', 'Users', 'Business', 'Platform', 'Transactions',
  'Forms', 'Chat', 'Network', 'Explore', 'CMS', 'Notifications',
  'Feature Gates', 'Visibility', 'Limits', 'Navigation', 'Public',
];

/** All 14 parameter codes. */
export const ALL_PARAMS = [
  'P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7',
  'P8', 'P9', 'P10', 'P11', 'P12', 'P13', 'P14',
];

/** Short display names for parameters (used in matrix column headers and gap reports). */
export const PARAM_NAMES: Record<string, string> = {
  P1: 'Render Integrity',
  P2: 'User Interaction',
  P3: 'Navigation',
  P4: 'Data Accuracy',
  P5: 'Auth & Authz',
  P6: 'Real-Time',
  P7: 'Error Handling',
  P8: 'Responsive',
  P9: 'Visual Regression',
  P10: 'Limits & Quotas',
  P11: 'Security',
  P12: 'Accessibility',
  P13: 'Cross-User',
  P14: 'State Persistence',
};

/** Full descriptions for each parameter. */
export const PARAMETER_DESCRIPTIONS: Record<ParameterType, string> = {
  P1: 'Render Integrity — page displays correctly',
  P2: 'User Interaction — clicks, forms, modals work',
  P3: 'Navigation — routing, back/forward, deep linking',
  P4: 'Data Accuracy — lists, detail, search, pagination match source',
  P5: 'Authentication & Authorization — login, roles, permissions',
  P6: 'Real-Time — WebSocket, live updates, presence',
  P7: 'Error Handling — 404, 403, 500, validation, rate limits',
  P8: 'Responsive — mobile viewport, hamburger menu',
  P9: 'Visual Regression — screenshot baselines',
  P10: 'Limits & Quotas — member quota, rate limits, field length',
  P11: 'Security — XSS, injection, CSRF, lockout',
  P12: 'Accessibility — ARIA, focus, keyboard nav',
  P13: 'Cross-User — two users interact simultaneously',
  P14: 'State Persistence — survives refresh, re-login, context switch',
};

// ---------------------------------------------------------------------------
// File Discovery
// ---------------------------------------------------------------------------

/** Recursively find all .spec.ts files under the given directory. */
export function findSpecFiles(dir: string): string[] {
  const results: string[] = [];
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      results.push(...findSpecFiles(fullPath));
    } else if (entry.name.endsWith('.spec.ts')) {
      results.push(fullPath);
    }
  }
  return results;
}

// ---------------------------------------------------------------------------
// Annotation Parsing
// ---------------------------------------------------------------------------

/**
 * Parse JSDoc annotations from a test file.
 *
 * Handles:
 * - Parenthetical qualifiers: `Chat (WebSocket)` → `Chat`
 * - Alias normalization: `user` → `Users`, `business` → `Business`
 * - Duplicate system dedup after normalization (e.g. `Auth (OAuth)` + `Auth`)
 *
 * @param filePath - Absolute path to the spec file
 * @param testsDir - Absolute path to the tests/ root (for relative path computation)
 */
export function parseAnnotations(filePath: string, testsDir: string): TestAnnotations | null {
  const content = fs.readFileSync(filePath, 'utf-8');

  const jsdocMatch = content.match(/\/\*\*([\s\S]*?)\*\//);
  if (!jsdocMatch) return null;

  const jsdoc = jsdocMatch[1];

  // Parse @layer
  const layerMatch = jsdoc.match(/@layer\s+(L[1-3])/);
  const layer = layerMatch ? layerMatch[1] : 'L1';

  // Parse @system — strip parenthetical qualifiers, normalize, dedup
  const systemMatch = jsdoc.match(/@system\s+(.+)/);
  const systems = systemMatch
    ? [
        ...new Set(
          systemMatch[1].split(',').map((s) => {
            const stripped = s.trim().replace(/\s*\(.*\)/, '');
            const normalized = stripped.toLowerCase();
            return SYSTEM_NORMALIZE[normalized] || stripped;
          }),
        ),
      ]
    : [];

  // Parse @parameters
  const paramMatch = jsdoc.match(/@parameters\s+(.+)/);
  const parameters = paramMatch ? (paramMatch[1].match(/P\d+/g) || []) : [];

  // Parse @priority
  const priorityMatch = jsdoc.match(/@priority\s+(\S+)/);
  const priority = priorityMatch ? priorityMatch[1] : 'medium';

  // Count test() calls
  const testMatches = content.match(/\btest\(/g);
  const testCount = testMatches ? testMatches.length : 0;

  const relativePath = path.relative(testsDir, filePath).replace(/\\/g, '/');

  return { filePath: relativePath, layer, systems, parameters, priority, testCount };
}
