/**
 * Generate Gap Report — cross-references the coverage matrix against
 * the system-feature-gap-analysis.md to identify remaining gaps.
 *
 * Usage: npx tsx scripts/generate-gap-report.ts
 * Output: docs/reports/gap-report.md
 */

import * as fs from 'fs';
import * as path from 'path';
import {
  type TestAnnotations,
  SYSTEM_NORMALIZE,
  findSpecFiles,
  parseAnnotations,
} from '../lib/report-annotations';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface GapEntry {
  system: string;
  area: string;
  status: 'covered' | 'partial' | 'missing' | 'deferred';
  notes: string;
}

// ---------------------------------------------------------------------------
// Expected Feature Areas (from architecture.md gap analysis)
// ---------------------------------------------------------------------------

const EXPECTED_FEATURES: Record<string, string[]> = {
  Auth: [
    'Login (valid/invalid)', 'Registration', 'Logout', 'Password reset',
    'Email verification', 'Password change', 'Session management', 'OAuth redirect',
  ],
  Users: [
    'Profile view', 'Profile edit', 'Settings/preferences', 'Home feed',
    'Activity feed', 'Other user profile', 'Username change',
  ],
  Business: [
    'Business creation', 'Business dashboard', 'Member management',
    'Role management', 'Business settings', 'Business lifecycle',
    'Member actions (suspend/ban)', 'Business visibility', 'Business network',
    'Business transactions', 'Business audit',
    'Role assignment', 'Permission changes', 'Custom roles',
  ],
  Platform: [
    'Platform dashboard', 'Platform management', 'Platform businesses',
    'Platform CMS', 'Platform forms', 'Platform transactions', 'Platform audit',
  ],
  Chat: [
    'Conversation list', 'Send message', 'Group chat', 'Attachments',
    'Reactions', 'Search messages', 'Chat requests', 'Message edit/delete',
    'Presence indicators', 'Delivery status', 'Group admin', 'Chat mute',
    'Entity sender badge',
  ],
  Network: [
    'Follow business', 'Connect user', 'Network page', 'Following list',
    'Connection list', 'Disconnect',
  ],
  Transactions: [
    'Membership invitation', 'Join request', 'Ownership transfer',
    'Transaction list', 'Transaction deny/cancel', 'Transaction pages',
    'Form mapping settings',
  ],
  Forms: [
    'Template builder', 'Form submission', 'Form responses',
    'Template lifecycle', 'Field CRUD', 'Field types (all 14+)',
  ],
  CMS: [
    'Site management', 'Page publish', 'Content editing',
    'Media library', 'API keys',
  ],
  Notifications: [
    'Notification center', 'Notification preferences', 'Notification history',
  ],
  Explore: [
    'Search businesses', 'Search users', 'Filters',
  ],
  'Feature Gates': [
    'Feature gate 403 + UI degradation',
  ],
  Visibility: [
    'Tier 2 visibility settings', 'Public view changes',
  ],
  Limits: [
    'Member quota', 'Rate limits', 'Field length limits',
  ],
  Navigation: [
    'Account switcher',
  ],
  Public: [
    'Landing pages',
  ],
};

// ---------------------------------------------------------------------------
// Directory-Name Heuristic
// ---------------------------------------------------------------------------

/**
 * Maps test directory names to canonical system names.
 * Used as a fallback when a file's @system annotation doesn't list a system
 * but the file physically lives in that system's directory.
 */
const DIR_TO_SYSTEM: Record<string, string> = {
  'auth': 'Auth',
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
  'limits': 'Limits',
  'navigation': 'Navigation',
  'public': 'Public',
  'responsive': 'Responsive',
};

/**
 * Infer additional system attribution from the directory path.
 * E.g., a file in tests/smoke/limits/ gets attributed to the Limits system
 * even if its @system annotation only says "business".
 */
function inferSystemFromPath(filePath: string): string | null {
  const parts = filePath.replace(/\\/g, '/').split('/');
  // Look for a known directory name in the path (closest to the file wins)
  for (let i = parts.length - 2; i >= 0; i--) {
    const dir = parts[i].toLowerCase();
    if (DIR_TO_SYSTEM[dir]) return DIR_TO_SYSTEM[dir];
  }
  return null;
}

// ---------------------------------------------------------------------------
// Gap Analysis
// ---------------------------------------------------------------------------

function analyzeGaps(annotations: TestAnnotations[]): GapEntry[] {
  const gaps: GapEntry[] = [];

  // Build a map of which systems have which files
  // Include directory-inferred systems for gap analysis
  const systemFiles = new Map<string, TestAnnotations[]>();
  for (const ann of annotations) {
    const allSystems = new Set(ann.systems);

    // Directory heuristic: also attribute the file to the directory's system
    const dirSystem = inferSystemFromPath(ann.filePath);
    if (dirSystem && dirSystem !== 'Responsive') {
      allSystems.add(dirSystem);
    }

    for (const sys of allSystems) {
      if (!systemFiles.has(sys)) systemFiles.set(sys, []);
      systemFiles.get(sys)!.push(ann);
    }
  }

  for (const [system, features] of Object.entries(EXPECTED_FEATURES)) {
    const files = systemFiles.get(system) || [];

    for (const feature of features) {
      const featureSlug = feature.toLowerCase().replace(/[^a-z0-9]/g, '');
      const hasFile = files.some((f) => {
        const fileSlug = f.filePath.toLowerCase().replace(/[^a-z0-9]/g, '');
        return fileSlug.includes(featureSlug) ||
          featureSlug.split(/(?=[a-z])/).some((word) => word.length > 3 && fileSlug.includes(word));
      });

      if (hasFile) {
        gaps.push({ system, area: feature, status: 'covered', notes: '' });
      } else if (files.length > 0) {
        const keywords = feature.toLowerCase().split(/[\s/()]+/).filter((w) => w.length > 3);
        const broadMatch = files.some((f) => {
          const fp = f.filePath.toLowerCase();
          return keywords.some((kw) => fp.includes(kw));
        });
        if (broadMatch) {
          gaps.push({ system, area: feature, status: 'partial', notes: 'Partially covered by related test file' });
        } else {
          gaps.push({ system, area: feature, status: 'missing', notes: '' });
        }
      } else {
        gaps.push({ system, area: feature, status: 'missing', notes: `No test files cover ${system} system` });
      }
    }
  }

  return gaps;
}

// ---------------------------------------------------------------------------
// Output
// ---------------------------------------------------------------------------

function generateGapReportMd(annotations: TestAnnotations[], gaps: GapEntry[]): string {
  const lines: string[] = [];
  const now = new Date().toISOString().split('T')[0];

  lines.push('# E2E Gap Report');
  lines.push('');
  lines.push(`> Auto-generated on ${now} by \`scripts/generate-gap-report.ts\``);
  lines.push(`> Cross-references ${annotations.length} test files against expected feature areas.`);
  lines.push('');

  // Summary
  const covered = gaps.filter((g) => g.status === 'covered').length;
  const partial = gaps.filter((g) => g.status === 'partial').length;
  const missing = gaps.filter((g) => g.status === 'missing').length;
  const deferred = gaps.filter((g) => g.status === 'deferred').length;
  const total = gaps.length;

  lines.push('## Summary');
  lines.push('');
  lines.push(`| Status | Count | % |`);
  lines.push(`|--------|-------|---|`);
  lines.push(`| Covered | ${covered} | ${((covered / total) * 100).toFixed(1)}% |`);
  lines.push(`| Partial | ${partial} | ${((partial / total) * 100).toFixed(1)}% |`);
  lines.push(`| Missing | ${missing} | ${((missing / total) * 100).toFixed(1)}% |`);
  if (deferred > 0) {
    lines.push(`| Deferred | ${deferred} | ${((deferred / total) * 100).toFixed(1)}% |`);
  }
  lines.push(`| **Total** | **${total}** | **100%** |`);
  lines.push('');

  // Per-system breakdown
  const systems = [...new Set(gaps.map((g) => g.system))];

  for (const sys of systems) {
    const sysGaps = gaps.filter((g) => g.system === sys);
    const sysCovered = sysGaps.filter((g) => g.status === 'covered' || g.status === 'partial').length;
    const sysTotal = sysGaps.length;

    lines.push(`## ${sys} (${sysCovered}/${sysTotal})`);
    lines.push('');
    lines.push('| Feature Area | Status | Notes |');
    lines.push('|-------------|--------|-------|');
    for (const gap of sysGaps) {
      const icon = gap.status === 'covered' ? 'covered' :
                   gap.status === 'partial' ? 'partial' :
                   gap.status === 'deferred' ? 'deferred' : '**MISSING**';
      lines.push(`| ${gap.area} | ${icon} | ${gap.notes} |`);
    }
    lines.push('');
  }

  // Action items
  const actionItems = gaps.filter((g) => g.status === 'missing');
  if (actionItems.length > 0) {
    lines.push('## Action Items');
    lines.push('');
    for (const item of actionItems) {
      lines.push(`- [ ] **${item.system}**: ${item.area}${item.notes ? ` — ${item.notes}` : ''}`);
    }
    lines.push('');
  }

  return lines.join('\n');
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

function main(): void {
  const testsDir = path.resolve(__dirname, '..', 'tests');
  const reportsDir = path.resolve(__dirname, '..', 'docs', 'reports');

  if (!fs.existsSync(reportsDir)) {
    fs.mkdirSync(reportsDir, { recursive: true });
  }

  // Discover and parse
  const specFiles = findSpecFiles(testsDir);
  const annotations: TestAnnotations[] = [];

  for (const file of specFiles) {
    const ann = parseAnnotations(file, testsDir);
    if (ann) annotations.push(ann);
  }

  console.log(`Parsed ${annotations.length} test files`);

  // Analyze gaps
  const gaps = analyzeGaps(annotations);

  // Generate markdown
  const reportMd = generateGapReportMd(annotations, gaps);

  // Write
  const outputPath = path.join(reportsDir, 'gap-report.md');
  fs.writeFileSync(outputPath, reportMd, 'utf-8');
  console.log(`Wrote ${outputPath}`);

  // Summary
  const covered = gaps.filter((g) => g.status === 'covered').length;
  const total = gaps.length;
  console.log(`\nGap analysis: ${covered}/${total} feature areas covered (${((covered / total) * 100).toFixed(1)}%)`);
}

main();
