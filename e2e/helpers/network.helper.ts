/**
 * Network helper — common network operations for tests.
 *
 * Provides API-based follow and connection setup.
 */

import type { ApiClient } from '../lib/api-client';

/** Follow a business via API. */
export async function followBusinessViaApi(
  api: ApiClient,
  businessId: string,
): Promise<{ id: string }> {
  const res = await api.post('network/follow/', {
    followee_type: 'business',
    followee_id: businessId,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`followBusinessViaApi failed (${res.status}): ${body}`);
  }
  return (await res.json()) as { id: string };
}

/** Unfollow a business via API. */
export async function unfollowBusinessViaApi(
  api: ApiClient,
  followId: string,
): Promise<void> {
  const res = await api.delete(`network/follow/${followId}/`);
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`unfollowBusinessViaApi failed (${res.status}): ${body}`);
  }
}

/** Send a user connection request via API (creates a transaction). */
export async function sendConnectionRequestViaApi(
  api: ApiClient,
  targetUserId: string,
  note?: string,
): Promise<Record<string, unknown>> {
  const body: Record<string, unknown> = {
    target_user_id: targetUserId,
  };
  if (note) body.note = note;
  const res = await api.post('network/connections/request/', body);
  if (!res.ok) {
    const errBody = await res.text();
    throw new Error(`sendConnectionRequestViaApi failed (${res.status}): ${errBody}`);
  }
  return (await res.json()) as Record<string, unknown>;
}

/** Get user's connections via API. */
export async function getConnectionsViaApi(
  api: ApiClient,
): Promise<{ results: Record<string, unknown>[] }> {
  const res = await api.get('network/connections/');
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`getConnectionsViaApi failed (${res.status}): ${body}`);
  }
  return (await res.json()) as { results: Record<string, unknown>[] };
}

/** Get user's following list via API. */
export async function getFollowingViaApi(
  api: ApiClient,
): Promise<{ results: Record<string, unknown>[] }> {
  const res = await api.get('network/following/');
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`getFollowingViaApi failed (${res.status}): ${body}`);
  }
  return (await res.json()) as { results: Record<string, unknown>[] };
}

/** Get business followers list via API. */
export async function getBusinessFollowersViaApi(
  api: ApiClient,
  businessSlug: string,
): Promise<{ results: Record<string, unknown>[] }> {
  const res = await api.get(`network/business/${businessSlug}/followers/`);
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`getBusinessFollowersViaApi failed (${res.status}): ${body}`);
  }
  return (await res.json()) as { results: Record<string, unknown>[] };
}
