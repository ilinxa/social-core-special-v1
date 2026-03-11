import { apiClient } from "@/lib/api-client";
import type { User, UserProfile, UserPublicWithRelationship, UserLimited } from "@/types";

// =============================================================================
// INPUT TYPES
// =============================================================================

export interface UpdateUsernameData {
  username: string;
}

export interface UpdateProfileData {
  first_name?: string;
  last_name?: string;
  phone?: string;
  bio?: string;
  timezone?: string;
  language?: string;
  country?: string;
  city?: string;
  tags?: string[];
  is_public?: boolean;
}

export interface CheckUsernameResponse {
  available: boolean;
  is_current: boolean;
}

// =============================================================================
// API FUNCTIONS
// =============================================================================

export async function fetchCurrentUserApi(): Promise<User> {
  const response = await apiClient.get<User>("/users/me/");
  return response.data;
}

export async function updateUsernameApi(data: UpdateUsernameData): Promise<User> {
  const response = await apiClient.patch<User>("/users/me/", data);
  return response.data;
}

export async function fetchProfileApi(): Promise<UserProfile> {
  const response = await apiClient.get<UserProfile>("/users/me/profile/");
  return response.data;
}

export async function updateProfileApi(data: UpdateProfileData): Promise<UserProfile> {
  const response = await apiClient.patch<UserProfile>("/users/me/profile/", data);
  return response.data;
}

export async function uploadAvatarApi(file: File): Promise<UserProfile> {
  const formData = new FormData();
  formData.append("avatar", file);
  const response = await apiClient.post<UserProfile>("/users/me/avatar/", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
}

export async function deleteAvatarApi(): Promise<void> {
  await apiClient.delete("/users/me/avatar/");
}

export async function uploadCoverImageApi(file: File): Promise<UserProfile> {
  const formData = new FormData();
  formData.append("cover_image", file);
  const response = await apiClient.post<UserProfile>("/users/me/cover-image/", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
}

export async function deleteCoverImageApi(): Promise<void> {
  await apiClient.delete("/users/me/cover-image/");
}

export async function checkUsernameApi(username: string): Promise<CheckUsernameResponse> {
  const response = await apiClient.get<CheckUsernameResponse>("/users/check-username/", {
    params: { username },
  });
  return response.data;
}

export async function fetchUserByUsernameApi(
  username: string,
): Promise<UserPublicWithRelationship | UserLimited> {
  const response = await apiClient.get<UserPublicWithRelationship | UserLimited>(`/users/${username}/`);
  return response.data;
}

export async function deactivateAccountApi(): Promise<void> {
  await apiClient.delete("/users/me/");
}
