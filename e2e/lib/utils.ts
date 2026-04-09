/**
 * Common utilities for E2E tests.
 */

import { randomUUID } from 'crypto';

/**
 * Generate a unique test email address.
 * Pattern: `test-{uuid}@e2e.com`
 */
export function generateEmail(prefix = 'test'): string {
  const id = randomUUID().slice(0, 8);
  return `${prefix}-${id}@e2e.com`;
}

/**
 * Generate a unique username from an email address.
 * Mirrors the backend pattern: local part, replace dots/hyphens with underscores, min 5 chars.
 */
export function usernameFromEmail(email: string): string {
  let username = email.split('@')[0].replace(/[.\-]/g, '_');
  if (username.length < 5) {
    username += '_user';
  }
  return username;
}

/**
 * Generate a unique test business name.
 */
export function generateBusinessName(prefix = 'E2E Biz'): string {
  const id = randomUUID().slice(0, 6);
  return `${prefix} ${id}`;
}

/**
 * Generate a unique slug from a name.
 */
export function slugify(name: string): string {
  return name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
}

/**
 * Retry an async function until it succeeds or max retries is reached.
 */
export async function retry<T>(
  fn: () => Promise<T>,
  options: { retries?: number; delay?: number; description?: string } = {},
): Promise<T> {
  const { retries = 15, delay = 1000, description = 'operation' } = options;

  for (let attempt = 1; attempt <= retries; attempt++) {
    try {
      return await fn();
    } catch (error) {
      if (attempt === retries) {
        throw new Error(
          `${description} failed after ${retries} attempts: ${error instanceof Error ? error.message : String(error)}`,
        );
      }
      await sleep(delay);
    }
  }

  // Unreachable, but TypeScript needs it
  throw new Error(`${description} failed`);
}

/**
 * Sleep for a specified number of milliseconds.
 */
export function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
