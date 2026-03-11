/**
 * Transaction system types matching backend API contracts.
 *
 * Backend source: apps.transaction.api.serializers, apps.transaction.types,
 *                 apps.transaction.constants, apps.transaction.policies
 */

import type { WithPermissions } from "@/types/api";

// =============================================================================
// ENUMS
// =============================================================================

export type TransactionStatus =
  | "created"
  | "pending"
  | "pending_review"
  | "accepted"
  | "denied"
  | "cancelled"
  | "expired"
  | "dismissed"
  | "invalidated"
  | "info_requested";

export type TransactionMode = "invitation" | "request";

export type TransactionCategory =
  | "membership"
  | "ownership"
  | "verification"
  | "permission"
  | "social";

export type PartyType = "user" | "account" | "membership_actor" | "system";

// =============================================================================
// TRANSACTION LOG
// =============================================================================

export type TransactionLog = {
  id: string;
  event_type: string;
  timestamp: string;
  previous_status: TransactionStatus | null;
  new_status: TransactionStatus | null;
  metadata: Record<string, unknown>;
};

// =============================================================================
// TRANSACTION — LIST
// =============================================================================

/** Lightweight transaction for list views (TransactionListSerializer). */
export type TransactionListItem = {
  id: string;
  transaction_type: string;
  mode: TransactionMode;
  status: TransactionStatus;
  category: TransactionCategory;
  initiator_type: PartyType;
  initiator_id: string;
  initiator_name: string;
  target_type: PartyType;
  target_id: string;
  target_name: string;
  context_type: string;
  context_id: string;
  expires_at: string | null;
  created_at: string;
};

// =============================================================================
// TRANSACTION — DETAIL
// =============================================================================

/** Embedded form response in transaction detail. */
export type TransactionFormResponse = {
  id: string;
  form_template_id: string;
  form_name: string | null;
  status: string;
  revision: number;
  submitted_at: string | null;
  data: Record<string, unknown>;
};

/** Embedded form mapping info in transaction detail. */
export type TransactionFormMappingEmbed = {
  id: string;
  form_template_id: string;
  form_template_name: string;
  is_required: boolean;
};

/** Full transaction for detail views (TransactionOutputSerializer). */
export type TransactionDetail = {
  id: string;
  transaction_type: string;
  mode: TransactionMode;
  initiator_type: PartyType;
  initiator_id: string;
  initiator_context: Record<string, unknown>;
  initiator_name: string;
  initiator_avatar_url: string | null;
  target_type: PartyType;
  target_id: string;
  target_name: string;
  target_avatar_url: string | null;
  context_type: string;
  context_id: string;
  status: TransactionStatus;
  payload: Record<string, unknown>;
  form_response_id: string | null;
  info_requested_at: string | null;
  info_requested_message: string | null;
  info_requested_fields: string[] | null;
  expires_at: string | null;
  resolved_at: string | null;
  resolution_reason: string;
  created_at: string;
  updated_at: string;
  logs: TransactionLog[];
  form_response: TransactionFormResponse | null;
  form_mapping: TransactionFormMappingEmbed | null;
};

// =============================================================================
// TRANSACTION TYPES CONFIG
// =============================================================================

/** From GET /transactions/types/ endpoint. */
export type TransactionTypeInfo = {
  id: string;
  name: string;
  mode: TransactionMode;
  category: TransactionCategory;
  context_type: string;
  requires_form: boolean;
  has_optional_form: boolean;
  user_configurable: boolean;
  expiration_days: number;
};

// =============================================================================
// FORM MAPPING
// =============================================================================

/** From TransactionFormMappingOutputSerializer. */
export type TransactionFormMapping = {
  id: string;
  account_type: string;
  account_id: string;
  transaction_type: string;
  form_template_id: string;
  form_template_name: string;
  is_required: boolean;
  created_at: string;
  updated_at: string;
};

// =============================================================================
// PERMISSION TYPES (from TransactionPolicy.get_viewer_permissions)
// =============================================================================

export type TransactionPermissions = {
  can_accept: boolean;
  can_approve: boolean;
  can_deny: boolean;
  can_cancel: boolean;
  can_dismiss: boolean;
  can_request_info: boolean;
  can_resubmit: boolean;
  can_view_form: boolean;
};

export type TransactionDetailWithPerms = TransactionDetail &
  WithPermissions<TransactionPermissions>;

// =============================================================================
// INPUT TYPES
// =============================================================================

export type CreateInvitationInput = {
  transaction_type: string;
  target_user_id: string;
  context_type: string;
  context_id: string;
  payload?: Record<string, unknown>;
  form_response_id?: string;
};

export type CreateRequestInput = {
  transaction_type: string;
  target_account_id?: string;
  target_account_type?: string;
  target_user_id?: string;
  payload?: Record<string, unknown>;
  form_response_id?: string;
};

export type AcceptInput = {
  role_id?: string;
  form_response_id?: string;
};

export type DenyInput = {
  reason?: string;
};

export type RequestInfoInput = {
  message: string;
  requested_fields?: string[];
};

export type FormResponseUpdateInput = {
  data: Record<string, unknown>;
};

export type CreateFormMappingInput = {
  account_type: string;
  account_id: string;
  transaction_type: string;
  form_template_id: string;
  is_required?: boolean;
};

// =============================================================================
// QUERY PARAMS
// =============================================================================

export type TransactionRole = "initiator" | "target" | "all";

export type TransactionListParams = {
  role?: TransactionRole;
  mode?: TransactionMode;
  status?: TransactionStatus;
  transaction_type?: string;
  context_type?: string;
  context_id?: string;
  page?: number;
  page_size?: number;
};
