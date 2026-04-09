/**
 * Generate Coverage Matrix — parses JSDoc annotations from all test files
 * and produces a markdown matrix: Systems x Parameters x Layers.
 *
 * Usage: npx tsx scripts/generate-coverage-matrix.ts
 * Output: docs/coverage-matrix.md + docs/parameter-checklist.md
 */

import * as fs from 'fs';
import * as path from 'path';
import {
  type TestAnnotations,
  CANONICAL_SYSTEMS,
  ALL_PARAMS,
  PARAM_NAMES,
  findSpecFiles,
  parseAnnotations,
} from '../lib/report-annotations';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface CoverageCell {
  layers: Set<string>;
  files: string[];
  testCount: number;
}

// ---------------------------------------------------------------------------
// Matrix Generation
// ---------------------------------------------------------------------------

function buildMatrix(annotations: TestAnnotations[]): Map<string, Map<string, CoverageCell>> {
  const matrix = new Map<string, Map<string, CoverageCell>>();

  for (const sys of CANONICAL_SYSTEMS) {
    const row = new Map<string, CoverageCell>();
    for (const param of ALL_PARAMS) {
      row.set(param, { layers: new Set(), files: [], testCount: 0 });
    }
    matrix.set(sys, row);
  }

  for (const ann of annotations) {
    for (const sys of ann.systems) {
      const row = matrix.get(sys);
      if (!row) continue;
      for (const param of ann.parameters) {
        const cell = row.get(param);
        if (!cell) continue;
        cell.layers.add(ann.layer);
        cell.files.push(ann.filePath);
        cell.testCount += ann.testCount;
      }
    }
  }

  return matrix;
}

function cellIcon(cell: CoverageCell): string {
  if (cell.layers.size === 0) return '-';
  const layers = Array.from(cell.layers).sort();
  if (layers.length === 3) return 'L1+L2+L3';
  if (layers.length === 2) return layers.join('+');
  return layers[0];
}

// ---------------------------------------------------------------------------
// Markdown Output
// ---------------------------------------------------------------------------

function generateCoverageMatrixMd(
  annotations: TestAnnotations[],
  matrix: Map<string, Map<string, CoverageCell>>,
): string {
  const lines: string[] = [];
  const now = new Date().toISOString().split('T')[0];

  lines.push('# E2E Coverage Matrix');
  lines.push('');
  lines.push(`> Auto-generated on ${now} by \`scripts/generate-coverage-matrix.ts\``);
  lines.push(`> **${annotations.length} test files** | **${annotations.reduce((s, a) => s + a.testCount, 0)} tests**`);
  lines.push('');

  // Summary by layer
  const byLayer: Record<string, { files: number; tests: number }> = {};
  for (const ann of annotations) {
    if (!byLayer[ann.layer]) byLayer[ann.layer] = { files: 0, tests: 0 };
    byLayer[ann.layer].files++;
    byLayer[ann.layer].tests += ann.testCount;
  }

  lines.push('## Layer Summary');
  lines.push('');
  lines.push('| Layer | Files | Tests |');
  lines.push('|-------|-------|-------|');
  for (const layer of ['L1', 'L2', 'L3']) {
    const data = byLayer[layer] || { files: 0, tests: 0 };
    lines.push(`| ${layer} | ${data.files} | ${data.tests} |`);
  }
  lines.push('');

  // System x Parameter matrix
  lines.push('## System x Parameter Matrix');
  lines.push('');
  lines.push('Cell values show which test layers cover that system+parameter combination.');
  lines.push('`-` = no coverage, `L1` = smoke only, `L1+L2` = smoke + workflow, etc.');
  lines.push('');

  const header = `| System | ${ALL_PARAMS.join(' | ')} |`;
  const separator = `|--------|${ALL_PARAMS.map(() => '---').join('|')}|`;
  lines.push(header);
  lines.push(separator);

  for (const sys of CANONICAL_SYSTEMS) {
    const row = matrix.get(sys)!;
    const cells = ALL_PARAMS.map((p) => cellIcon(row.get(p)!));
    lines.push(`| **${sys}** | ${cells.join(' | ')} |`);
  }
  lines.push('');

  // Coverage statistics
  let covered = 0;
  let total = 0;
  for (const sys of CANONICAL_SYSTEMS) {
    const row = matrix.get(sys)!;
    for (const param of ALL_PARAMS) {
      total++;
      if (row.get(param)!.layers.size > 0) covered++;
    }
  }
  const pct = ((covered / total) * 100).toFixed(1);
  lines.push(`## Coverage: ${covered}/${total} cells (${pct}%)`);
  lines.push('');

  // Gaps
  lines.push('## Uncovered Cells');
  lines.push('');
  const gaps: string[] = [];
  for (const sys of CANONICAL_SYSTEMS) {
    const row = matrix.get(sys)!;
    for (const param of ALL_PARAMS) {
      if (row.get(param)!.layers.size === 0) {
        gaps.push(`- **${sys}** x **${param}** (${PARAM_NAMES[param]})`);
      }
    }
  }
  if (gaps.length === 0) {
    lines.push('All system x parameter combinations are covered!');
  } else {
    lines.push(...gaps);
  }
  lines.push('');

  return lines.join('\n');
}

function generateParameterChecklistMd(annotations: TestAnnotations[]): string {
  const lines: string[] = [];
  const now = new Date().toISOString().split('T')[0];

  lines.push('# E2E Parameter Checklist');
  lines.push('');
  lines.push(`> Auto-generated on ${now} by \`scripts/generate-coverage-matrix.ts\``);
  lines.push('');

  for (const param of ALL_PARAMS) {
    const name = PARAM_NAMES[param];
    const matching = annotations.filter((a) => a.parameters.includes(param));
    lines.push(`## ${param} — ${name}`);
    lines.push('');
    if (matching.length === 0) {
      lines.push('No test files cover this parameter.');
    } else {
      lines.push(`**${matching.length} files, ${matching.reduce((s, a) => s + a.testCount, 0)} tests**`);
      lines.push('');
      lines.push('| File | Layer | Systems | Tests |');
      lines.push('|------|-------|---------|-------|');
      for (const ann of matching) {
        lines.push(`| ${ann.filePath} | ${ann.layer} | ${ann.systems.join(', ')} | ${ann.testCount} |`);
      }
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
  const docsDir = path.resolve(__dirname, '..', 'docs');

  // Discover and parse
  const specFiles = findSpecFiles(testsDir);
  const annotations: TestAnnotations[] = [];

  for (const file of specFiles) {
    const ann = parseAnnotations(file, testsDir);
    if (ann) {
      annotations.push(ann);
    } else {
      console.warn(`Warning: No JSDoc annotations found in ${file}`);
    }
  }

  console.log(`Parsed ${annotations.length} test files`);
  console.log(`Total tests: ${annotations.reduce((s, a) => s + a.testCount, 0)}`);

  // Build matrix
  const matrix = buildMatrix(annotations);

  // Generate markdown
  const coverageMd = generateCoverageMatrixMd(annotations, matrix);
  const checklistMd = generateParameterChecklistMd(annotations);

  // Write files
  fs.writeFileSync(path.join(docsDir, 'coverage-matrix.md'), coverageMd, 'utf-8');
  console.log(`Wrote docs/coverage-matrix.md`);

  fs.writeFileSync(path.join(docsDir, 'parameter-checklist.md'), checklistMd, 'utf-8');
  console.log(`Wrote docs/parameter-checklist.md`);

  // Summary
  let covered = 0;
  let total = 0;
  for (const sys of CANONICAL_SYSTEMS) {
    const row = matrix.get(sys)!;
    for (const param of ALL_PARAMS) {
      total++;
      if (row.get(param)!.layers.size > 0) covered++;
    }
  }
  console.log(`\nCoverage: ${covered}/${total} cells (${((covered / total) * 100).toFixed(1)}%)`);
}

main();
