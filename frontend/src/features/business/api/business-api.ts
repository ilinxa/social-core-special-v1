import { apiClient } from "@/lib/api-client";
import { buildFormDataIfNeeded } from "@/lib/form-data-utils";
import type {
  BusinessAccount,
  BusinessAccountList,
  BusinessAccountWithRelationship,
  BusinessProfile,
} from "@/types/organization";

// =============================================================================
// INPUT TYPES
// =============================================================================

export interface CreateBusinessData {
  legal_name: string;
  country: string;
  slug?: string;
  business_type?: string;
  registration_number?: string;
  tax_id?: string;
  legal_address?: string;
  display_name?: string;
}

export interface UpdateBusinessData {
  legal_name?: string;
  registration_number?: string;
  tax_id?: string;
  country?: string;
  city?: string;
  legal_address?: string;
  business_type?: string;
  settings?: Record<string, unknown>;
  open_member_request?: boolean;
}

export interface UpdateBusinessProfileData {
  display_name?: string;
  tagline?: string;
  description?: string;
  logo?: File | null;
  cover_image?: File | null;
  website?: string;
  contact_email?: string;
  contact_phone?: string;
  industry?: string;
  company_size?: string;
  founded_year?: number | null;
  social_links?: Record<string, string>;
  tags?: string[];
  is_public?: boolean;
}

// =============================================================================
// API FUNCTIONS
// =============================================================================

export async function fetchMyBusinessesApi(): Promise<BusinessAccountList[]> {
  const response = await apiClient.get<BusinessAccountList[]>("/business/my/");
  return response.data;
}

export async function fetchBusinessApi(slug: string): Promise<BusinessAccountWithRelationship> {
  const response = await apiClient.get<BusinessAccountWithRelationship>(`/business/${slug}/`);
  return response.data;
}

export async function createBusinessApi(data: CreateBusinessData): Promise<BusinessAccount> {
  const response = await apiClient.post<BusinessAccount>("/business/", data);
  return response.data;
}

export async function updateBusinessApi(
  slug: string,
  data: UpdateBusinessData,
): Promise<BusinessAccount> {
  const response = await apiClient.patch<BusinessAccount>(`/business/${slug}/`, data);
  return response.data;
}

export async function archiveBusinessApi(slug: string): Promise<BusinessAccount> {
  const response = await apiClient.post<BusinessAccount>(`/business/${slug}/archive/`);
  return response.data;
}

export async function deleteBusinessApi(slug: string): Promise<void> {
  await apiClient.delete(`/business/${slug}/`);
}

export async function updateBusinessProfileApi(
  slug: string,
  data: UpdateBusinessProfileData,
): Promise<BusinessProfile> {
  const payload = buildFormDataIfNeeded(data as Record<string, unknown>);
  const headers = payload instanceof FormData
    ? { "Content-Type": "multipart/form-data" }
    : undefined;
  const response = await apiClient.patch<BusinessProfile>(
    `/business/${slug}/profile/`,
    payload,
    { headers },
  );
  return response.data;
}
