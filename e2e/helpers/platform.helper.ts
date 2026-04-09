/**
 * Platform helper — common platform operations for tests.
 *
 * Provides API-based platform management and data setup.
 */

import type { ApiClient } from '../lib/api-client';

/** Get the platform account via API. */
export async function getPlatformViaApi(
  api: ApiClient,
): Promise<Record<string, unknown>> {
  const res = await api.get('platform/account/');
  return (await res.json()) as Record<string, unknown>;
}

/** Get platform members list via API. */
export async function getPlatformMembersViaApi(
  api: ApiClient,
  params?: { status?: string; search?: string },
): Promise<{ count: number; results: Record<string, unknown>[] }> {
  const query = new URLSearchParams();
  if (params?.status) query.set('status', params.status);
  if (params?.search) query.set('search', params.search);
  const qs = query.toString();
  const res = await api.get(`platform/members/${qs ? `?${qs}` : ''}`);
  return (await res.json()) as { count: number; results: Record<string, unknown>[] };
}

/** Get platform roles list via API. */
export async function getPlatformRolesViaApi(
  api: ApiClient,
): Promise<Record<string, unknown>[]> {
  const res = await api.get('platform/roles/');
  return (await res.json()) as Record<string, unknown>[];
}

/** Update platform profile via API. */
export async function updatePlatformProfileViaApi(
  api: ApiClient,
  data: Record<string, unknown>,
): Promise<Record<string, unknown>> {
  const res = await api.patch('platform/profile/', data);
  return (await res.json()) as Record<string, unknown>;
}
