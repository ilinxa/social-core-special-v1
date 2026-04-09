/**
 * Transaction helper — common transaction operations for tests.
 *
 * Provides API-based transaction creation and management.
 */

import type { ApiClient } from '../lib/api-client';
import { getBaseMemberRoleId } from './business.helper';

/** Create a membership invitation via API. */
export async function createInvitationViaApi(
  api: ApiClient,
  data: {
    targetUserId: string;
    contextType: string;
    contextId: string;
    transactionType?: string;
    payload?: Record<string, unknown>;
  },
): Promise<Record<string, unknown>> {
  const res = await api.post('transactions/invitation/', {
    transaction_type: data.transactionType ?? 'business_membership_invitation',
    target_user_id: data.targetUserId,
    context_type: data.contextType,
    context_id: data.contextId,
    payload: data.payload ?? {},
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`createInvitationViaApi failed (${res.status}): ${body}`);
  }
  return (await res.json()) as Record<string, unknown>;
}

/** Create a join request via API. */
export async function createJoinRequestViaApi(
  api: ApiClient,
  data: {
    contextType: string;
    contextId: string;
    transactionType?: string;
    formResponseId?: string;
  },
): Promise<Record<string, unknown>> {
  const body: Record<string, unknown> = {
    transaction_type: data.transactionType ?? 'business_membership_request',
    target_account_id: data.contextId,
    target_account_type: data.contextType,
  };
  if (data.formResponseId) body.form_response_id = data.formResponseId;
  const res = await api.post('transactions/request/', body);
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`createJoinRequestViaApi failed (${res.status}): ${body}`);
  }
  return (await res.json()) as Record<string, unknown>;
}

/** Accept a transaction via API. */
export async function acceptTransactionViaApi(
  api: ApiClient,
  transactionId: string,
): Promise<void> {
  const res = await api.post(`transactions/${transactionId}/accept/`);
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`acceptTransactionViaApi failed (${res.status}): ${body}`);
  }
}

/** Deny a transaction via API. */
export async function denyTransactionViaApi(
  api: ApiClient,
  transactionId: string,
  reason?: string,
): Promise<void> {
  const body: Record<string, unknown> = {};
  if (reason) body.reason = reason;
  const res = await api.post(`transactions/${transactionId}/deny/`, body);
  if (!res.ok) {
    const errBody = await res.text();
    throw new Error(`denyTransactionViaApi failed (${res.status}): ${errBody}`);
  }
}

/** Cancel a transaction via API. */
export async function cancelTransactionViaApi(
  api: ApiClient,
  transactionId: string,
): Promise<void> {
  const res = await api.post(`transactions/${transactionId}/cancel/`);
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`cancelTransactionViaApi failed (${res.status}): ${body}`);
  }
}

/** Get transaction details via API. */
export async function getTransactionViaApi(
  api: ApiClient,
  transactionId: string,
): Promise<Record<string, unknown>> {
  const res = await api.get(`transactions/${transactionId}/`);
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`getTransactionViaApi failed (${res.status}): ${body}`);
  }
  return (await res.json()) as Record<string, unknown>;
}

/** List user's transactions via API. */
export async function listTransactionsViaApi(
  api: ApiClient,
  params?: { role?: string; status?: string },
): Promise<{ results: Record<string, unknown>[] }> {
  const query = new URLSearchParams();
  if (params?.role) query.set('role', params.role);
  if (params?.status) query.set('status', params.status);
  const qs = query.toString();
  const res = await api.get(`transactions/${qs ? `?${qs}` : ''}`);
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`listTransactionsViaApi failed (${res.status}): ${body}`);
  }
  return (await res.json()) as { results: Record<string, unknown>[] };
}

/** Create an ownership transfer via API. */
export async function createOwnershipTransferViaApi(
  api: ApiClient,
  data: {
    targetUserId: string;
    contextType: string;
    contextId: string;
  },
): Promise<Record<string, unknown>> {
  const res = await api.post('transactions/invitation/', {
    transaction_type: `${data.contextType}_ownership_transfer`,
    target_user_id: data.targetUserId,
    context_type: data.contextType,
    context_id: data.contextId,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`createOwnershipTransferViaApi failed (${res.status}): ${body}`);
  }
  return (await res.json()) as Record<string, unknown>;
}

/** Approve a pending-review transaction via API. */
export async function approveTransactionViaApi(
  api: ApiClient,
  transactionId: string,
): Promise<void> {
  const res = await api.post(`transactions/${transactionId}/approve/`);
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`approveTransactionViaApi failed (${res.status}): ${body}`);
  }
}

/** Create a form-transaction mapping via API. */
export async function createFormMappingViaApi(
  api: ApiClient,
  data: {
    transactionType: string;
    templateId: string;
    accountType: string;
    accountId: string;
    isRequired?: boolean;
  },
): Promise<Record<string, unknown>> {
  const res = await api.post('transactions/form-mappings/', {
    transaction_type: data.transactionType,
    form_template_id: data.templateId,
    account_type: data.accountType,
    account_id: data.accountId,
    is_required: data.isRequired ?? true,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`createFormMappingViaApi failed (${res.status}): ${body}`);
  }
  return (await res.json()) as Record<string, unknown>;
}

/**
 * Convenience: invite a user to a business with automatic role lookup.
 * Looks up the base "member" role and includes it in the payload.
 */
export async function inviteToBusinessViaApi(
  api: ApiClient,
  slug: string,
  bizId: string,
  targetUserId: string,
): Promise<Record<string, unknown>> {
  const roleId = await getBaseMemberRoleId(api, slug);
  return createInvitationViaApi(api, {
    targetUserId,
    contextType: 'business',
    contextId: bizId,
    payload: { role_id: roleId },
  });
}
