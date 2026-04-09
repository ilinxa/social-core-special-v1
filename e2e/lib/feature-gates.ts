/**
 * Feature gate configuration reader for conditional test execution.
 *
 * Reads `deployment_config.json` and provides methods to check if
 * systems, features, and limits are enabled. Tests use this for
 * conditional `test.skip()` when features are disabled.
 *
 * In E2E, all gates are enabled by default (full deployment config).
 */

import * as fs from 'fs';
import * as path from 'path';
import { DEPLOYMENT_CONFIG_PATH } from './constants';

type DeploymentConfig = {
  org_mode?: string;
  systems?: Record<string, boolean>;
  features?: Record<string, unknown>;
  limits?: Record<string, unknown>;
  values?: Record<string, unknown>;
};

let config: DeploymentConfig | null = null;

/**
 * Load (or reload) the deployment config from disk.
 */
function loadConfig(): DeploymentConfig {
  try {
    const fullPath = path.resolve(__dirname, '..', DEPLOYMENT_CONFIG_PATH);
    const raw = fs.readFileSync(fullPath, 'utf-8');
    config = JSON.parse(raw) as DeploymentConfig;
    return config;
  } catch {
    // Missing config defaults to most restrictive state
    config = {};
    return config;
  }
}

function getConfig(): DeploymentConfig {
  if (!config) loadConfig();
  return config!;
}

/**
 * Navigate a nested config by dot-separated path.
 * Example: `getNestedValue("chat.attachments")` → `config.features.chat.attachments`
 */
function getNestedValue(obj: Record<string, unknown>, dotPath: string): unknown {
  const parts = dotPath.split('.');
  let current: unknown = obj;
  for (const part of parts) {
    if (current == null || typeof current !== 'object') return undefined;
    current = (current as Record<string, unknown>)[part];
  }
  return current;
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Check if a system is enabled (e.g., "chat", "cms", "network").
 * Defaults to false if not configured.
 */
export function isSystemEnabled(systemName: string): boolean {
  const cfg = getConfig();
  return cfg.systems?.[systemName] === true;
}

/**
 * Check if a feature is enabled (dot-path into features config).
 * Example: `isFeatureEnabled("chat.attachments")`
 * Defaults to false if not configured.
 */
export function isFeatureEnabled(featurePath: string): boolean {
  const cfg = getConfig();
  if (!cfg.features) return false;
  return getNestedValue(cfg.features as Record<string, unknown>, featurePath) === true;
}

/**
 * Get a numeric limit value.
 * Example: `getLimit("organization.business.max_members")`
 * Defaults to 0 (unlimited) if not configured.
 */
export function getLimit(limitPath: string): number {
  const cfg = getConfig();
  if (!cfg.limits) return 0;
  const val = getNestedValue(cfg.limits as Record<string, unknown>, limitPath);
  return typeof val === 'number' ? val : 0;
}

/**
 * Get a config value with default.
 */
export function getValue<T>(valuePath: string, defaultValue: T): T {
  const cfg = getConfig();
  if (!cfg.values) return defaultValue;
  const val = getNestedValue(cfg.values as Record<string, unknown>, valuePath);
  return (val as T) ?? defaultValue;
}

/**
 * Get the organization mode: "full", "user_and_platform", or "user_only".
 */
export function getOrgMode(): string {
  return getConfig().org_mode ?? 'user_only';
}

/**
 * Force reload the config from disk.
 */
export function reload(): void {
  config = null;
  loadConfig();
}
