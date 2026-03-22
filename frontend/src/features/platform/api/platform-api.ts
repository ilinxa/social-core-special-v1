import { apiClient } from "@/lib/api-client";
import { buildFormDataIfNeeded } from "@/lib/form-data-utils";
import type {
  PlatformAccount,
  PlatformAccountWithRelationship,
  PlatformProfile,
} from "@/types/organization";

// =============================================================================
// INPUT TYPES
// =============================================================================

export interface UpdatePlatformProfileData {
  name?: string;
  tagline?: string;
  description?: string;
  logo?: File | null;
  favicon?: File | null;
  primary_color?: string;
  secondary_color?: string;
  contact_email?: string;
  contact_phone?: string;
  address?: string;
  social_links?: Record<string, string>;
}

export interface UpdatePlatformSettingsData {
  settings?: Record<string, unknown>;
  open_member_request?: boolean;
}

// =============================================================================
// API FUNCTIONS
// =============================================================================

export async function fetchPlatformAccountApi(): Promise<PlatformAccountWithRelationship> {
  const response = await apiClient.get<PlatformAccountWithRelationship>("/platform/account/");
  return response.data;
}

export async function updatePlatformProfileApi(
  data: UpdatePlatformProfileData,
): Promise<PlatformProfile> {
  const payload = buildFormDataIfNeeded(data as Record<string, unknown>);
  const headers = payload instanceof FormData
    ? { "Content-Type": "multipart/form-data" }
    : undefined;
  const response = await apiClient.patch<PlatformProfile>(
    "/platform/profile/",
    payload,
    { headers },
  );
  return response.data;
}

export async function updatePlatformSettingsApi(
  data: UpdatePlatformSettingsData,
): Promise<PlatformAccount> {
  const response = await apiClient.patch<PlatformAccount>("/platform/settings/", data);
  return response.data;
}
