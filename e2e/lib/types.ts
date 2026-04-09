/**
 * Shared TypeScript types for E2E tests.
 */

// --- API Response Wrappers ---

export type ApiErrorResponse = {
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  };
};

// --- Auth ---

export type AuthTokens = {
  access_token: string;
  refresh_token: string;
};

export type AuthUser = {
  id: string;
  email: string;
  username: string;
  is_verified: boolean;
};

export type RegisterResponse = {
  is_new_user: boolean;
  user: AuthUser;
  tokens: AuthTokens;
};

export type LoginResponse = {
  user: AuthUser;
  tokens: AuthTokens;
};

// --- Business ---

export type Business = {
  id: string;
  legal_name: string;
  slug: string;
  country: string;
  status: string;
  max_members: number;
};

// --- Platform ---

export type Platform = {
  id: string;
  name: string;
  configured: boolean;
};

// --- Membership ---

export type Membership = {
  id: string;
  user_id: string;
  account_type: 'business' | 'platform';
  account_id: string;
  role_id: string;
  status: string;
  is_owner: boolean;
};

// --- Transaction ---

export type Transaction = {
  id: string;
  transaction_type: string;
  status: string;
  initiator_user_id: string;
  target_user_id: string;
  context_type: string;
  context_id: string;
};

// --- Test State ---

export type StoredUser = {
  id: string;
  email: string;
  username: string;
  accessToken: string;
  refreshToken: string;
};

export type StoredBusiness = {
  id: string;
  slug: string;
  ownerEmail: string;
};

export type TestStateData = {
  users: Record<string, StoredUser>;
  businesses: Record<string, StoredBusiness>;
  platform: { id: string; configured: boolean } | null;
};

// --- CMS ---

export type CmsSite = {
  id: string;
  slug: string;
  name: string;
  domain?: string;
  description?: string;
  is_active: boolean;
};

export type CmsPage = {
  id: string;
  slug: string;
  title: string;
  status: 'draft' | 'published' | 'archived';
  path: string;
  page_type: string;
  is_required: boolean;
  order: number;
};

export type CmsApiKey = {
  id: string;
  key?: string;
  key_prefix?: string;
  name: string;
  is_active: boolean;
  site_id: string;
};

export type CmsBlockPlacement = {
  id: string;
  draft_content: Record<string, unknown>;
  published_content: Record<string, unknown> | null;
  status: 'draft' | 'published';
};

export type CmsContentVersion = {
  version_number: number;
  action: 'draft_save' | 'publish' | 'rollback' | 'import';
  content: Record<string, unknown>;
  created_at: string;
  created_by?: string;
  notes?: string;
};

export type CmsMediaFile = {
  id: string;
  name: string;
  mime_type: string;
  size: number;
  url: string;
};

export type CmsTemplate = {
  id: string;
  display_name: string;
  slug: string;
  org_type: 'system' | 'platform' | 'business' | 'all';
  is_default: boolean;
  schema_version?: number;
};

export type CmsTemplateActivation = {
  id: string;
  template: CmsTemplate;
};

export type CmsPermissions = {
  can_view_content: boolean;
  can_edit_content: boolean;
  can_publish_content: boolean;
  can_create_site: boolean;
  can_edit_site: boolean;
  can_delete_site: boolean;
  can_create_page: boolean;
  can_edit_page: boolean;
  can_delete_page: boolean;
  can_upload_media: boolean;
  can_edit_media: boolean;
  can_delete_media: boolean;
  can_create_api_key: boolean;
  can_activate_template: boolean;
};

// --- Notifications ---

export type NotificationPreference = {
  notification_type: string;
  display_name: string;
  description: string;
  category: string;
  user_configurable: boolean;
  email_enabled: boolean;
  push_enabled: boolean;
  sms_enabled: boolean;
};

export type NotificationLogItem = {
  id: string;
  notification_type: string;
  scope_type: 'user' | 'business' | 'platform';
  scope_id: string | null;
  channels: string[];
  context: Record<string, unknown>;
  status: 'pending' | 'sent' | 'failed' | 'partial';
  channel_results: Record<string, { status: string; error?: string }>;
  created_at: string;
};

export type NotificationHistoryResponse = {
  notifications: NotificationLogItem[];
  count: number;
};

export type NotificationScopesResponse = {
  scopes: Array<{ scope_type: string; scope_id: string | null; count: number }>;
  count: number;
};

export type NotificationTypesResponse = {
  types: Array<{
    name: string;
    display_name: string;
    description: string;
    category: string;
    default_channels: string[];
  }>;
  count: number;
};

export type NotificationPermissions = {
  can_view_notifications: boolean;
  can_manage_preferences: boolean;
  can_manage_org_notifications: boolean;
};
