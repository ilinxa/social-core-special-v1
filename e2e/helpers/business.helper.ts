/**
 * Business helper — common business operations for tests.
 *
 * Provides API-based business creation, member management, and data setup.
 */

import type { ApiClient } from '../lib/api-client';
import type { DbClient } from '../lib/db-client';

/** Create a business via API and raise its member quota. */
export async function createBusinessViaApi(
  api: ApiClient,
  db: DbClient,
  data: {
    legalName: string;
    country?: string;
    companySize?: string;
  },
): Promise<{ id: string; slug: string; legalName: string }> {
  const res = await api.post('business/', {
    legal_name: data.legalName,
    country: data.country ?? 'US',
    company_size: data.companySize ?? 'small',
  });
  if (!res.ok) {
    const errBody = await res.text();
    throw new Error(`createBusinessViaApi failed (${res.status}): ${errBody}`);
  }
  const body = (await res.json()) as Record<string, string>;

  // Raise member quota from default 1 to 10
  await db.setBusinessMaxMembers(body.id, 10);
  await db.setBusinessOpenMemberRequest(body.id, true);

  return {
    id: body.id,
    slug: body.slug,
    legalName: body.legal_name,
  };
}

/** Get a business by slug via API. */
export async function getBusinessViaApi(
  api: ApiClient,
  slug: string,
): Promise<Record<string, unknown>> {
  const res = await api.get(`business/${slug}/`);
  return (await res.json()) as Record<string, unknown>;
}

/** Update business profile via API. */
export async function updateBusinessProfileViaApi(
  api: ApiClient,
  slug: string,
  data: Record<string, unknown>,
): Promise<Record<string, unknown>> {
  const res = await api.patch(`business/${slug}/profile/`, data);
  return (await res.json()) as Record<string, unknown>;
}

/** Get business members list via API. */
export async function getBusinessMembersViaApi(
  api: ApiClient,
  slug: string,
  params?: { status?: string; search?: string },
): Promise<{ count: number; results: Record<string, unknown>[] }> {
  const query = new URLSearchParams();
  if (params?.status) query.set('status', params.status);
  if (params?.search) query.set('search', params.search);
  const qs = query.toString();
  const res = await api.get(`business/${slug}/members/${qs ? `?${qs}` : ''}`);
  return (await res.json()) as { count: number; results: Record<string, unknown>[] };
}

/** Get business roles list via API. */
export async function getBusinessRolesViaApi(
  api: ApiClient,
  slug: string,
): Promise<Record<string, unknown>[]> {
  const res = await api.get(`business/${slug}/roles/`);
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`getBusinessRolesViaApi failed (${res.status}): ${body}`);
  }
  return (await res.json()) as Record<string, unknown>[];
}

/** Get the base "member" role ID for a business. */
export async function getBaseMemberRoleId(
  api: ApiClient,
  slug: string,
): Promise<string> {
  const roles = await getBusinessRolesViaApi(api, slug);
  const memberRole = roles.find(
    (r) => {
      const name = (r as { name: string }).name.toLowerCase();
      return name === 'member' || name === 'base member';
    },
  );
  if (!memberRole) {
    throw new Error(`No "member" role found for business ${slug}. Available: ${roles.map((r) => (r as { name: string }).name).join(', ')}`);
  }
  return (memberRole as { id: string }).id;
}

/** Suspend a business via API. */
export async function suspendBusinessViaApi(
  api: ApiClient,
  slug: string,
): Promise<void> {
  await api.post(`business/${slug}/suspend/`, {});
}

/** Reactivate a business via API. */
export async function reactivateBusinessViaApi(
  api: ApiClient,
  slug: string,
): Promise<void> {
  await api.post(`business/${slug}/reactivate/`, {});
}

/** Archive a business via API. */
export async function archiveBusinessViaApi(
  api: ApiClient,
  slug: string,
): Promise<void> {
  await api.post(`business/${slug}/archive/`, {});
}

/** Assign a role to a business member via API. */
export async function assignRoleViaApi(
  api: ApiClient,
  slug: string,
  memberId: string,
  roleId: string,
): Promise<void> {
  await api.patch(`business/${slug}/members/${memberId}/role/`, { role_id: roleId });
}

/** Remove a business member via API. */
export async function removeBusinessMemberViaApi(
  api: ApiClient,
  slug: string,
  memberId: string,
): Promise<void> {
  await api.post(`business/${slug}/members/${memberId}/remove/`, {});
}

/** Suspend a business member via API. */
export async function suspendMemberViaApi(
  api: ApiClient,
  slug: string,
  memberId: string,
): Promise<void> {
  await api.post(`business/${slug}/members/${memberId}/suspend/`, {});
}

/** Reactivate a business member via API. */
export async function reactivateMemberViaApi(
  api: ApiClient,
  slug: string,
  memberId: string,
): Promise<void> {
  await api.post(`business/${slug}/members/${memberId}/reactivate/`, {});
}
