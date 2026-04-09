/**
 * Notification System Types
 * =========================
 * TypeScript types matching backend notification serializer shapes exactly.
 *
 * Backend source: apps.notifications.serializers, apps.notifications.constants
 */

import type { WithPermissions } from "@/types/api";

// =============================================================================
// ENUMS (union literal types matching backend TextChoices)
// =============================================================================

export type NotificationScope = "user" | "business" | "platform";

export type NotificationStatus =
  | "pending"
  | "sent"
  | "partial"
  | "failed"
  | "processing"
  | "retrying";

export type NotificationCategory =
  | "auth"
  | "security"
  | "transactional"
  | "marketing"
  | "social";

// =============================================================================
// DOMAIN TYPES — matching backend output serializers exactly
// =============================================================================

/** NotificationLogItem from NotificationLogSerializer */
export type NotificationLogItem = {
  id: string;
  notification_type: string;
  scope_type: NotificationScope;
  scope_id: string | null;
  channels: string[];
  context: Record<string, unknown>;
  status: NotificationStatus;
  channel_results: Record<string, { status: string; error?: string }>;
  created_at: string;
};

/** Scope summary item from NotificationScopesView */
export type NotificationScopeItem = {
  scope_type: NotificationScope;
  scope_id: string | null;
  count: number;
};

/** PreferenceItem from AllPreferencesSerializer */
export type PreferenceItem = {
  notification_type: string;
  display_name: string;
  description: string;
  category: NotificationCategory;
  user_configurable: boolean;
  email_enabled: boolean;
  push_enabled: boolean;
  sms_enabled: boolean;
};

/** ConfigurableType from ConfigurableTypeSerializer */
export type ConfigurableType = {
  name: string;
  display_name: string;
  description: string;
  category: string;
  default_channels: string[];
};

// =============================================================================
// PERMISSIONS — from history endpoint when scope_id provided
// =============================================================================

export type NotificationPermissions = {
  can_view_notifications: boolean;
  can_manage_preferences: boolean;
  can_manage_org_notifications: boolean;
};

// =============================================================================
// API RESPONSE TYPES
// =============================================================================

export type NotificationHistoryResponse = {
  notifications: NotificationLogItem[];
  count: number;
};

export type NotificationHistoryWithPerms = NotificationHistoryResponse &
  WithPermissions<NotificationPermissions>;

export type NotificationScopesResponse = {
  scopes: NotificationScopeItem[];
  count: number;
};

/** Preferences grouped by category from AllPreferencesSerializer */
export type NotificationPreferencesResponse = Record<string, PreferenceItem[]>;

export type NotificationTypesResponse = {
  types: ConfigurableType[];
  count: number;
};

// =============================================================================
// INPUT TYPES — matching backend input serializers
// =============================================================================

export type NotificationHistoryParams = {
  notification_type?: string;
  status?: NotificationStatus;
  limit?: number;
  offset?: number;
  scope_type?: NotificationScope;
  scope_id?: string;
};

export type UpdatePreferenceInput = {
  email_enabled?: boolean;
  push_enabled?: boolean;
  sms_enabled?: boolean;
};
