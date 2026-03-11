import { apiClient } from "@/lib/api-client";
import type { PaginatedResponse, PaginationParams } from "@/types";
import type {
  FollowingItem,
  FollowerItem,
  UserConnectionItem,
  AccountConnectionItem,
  NetworkStats,
} from "@/types/network";

// =============================================================================
// INPUT TYPES
// =============================================================================

export interface CreateFollowData {
  followee_type: "business" | "platform";
  followee_id: string;
}

export interface CreateConnectionData {
  target_user_id: string;
  note?: string;
}

export interface CreateBusinessConnectionData {
  target_account_type: string;
  target_account_id: string;
  note?: string;
}

export interface FollowingParams extends PaginationParams {
  type?: "business" | "platform";
}

export interface ConnectionsParams extends PaginationParams {
  status?: string;
  search?: string;
}

export interface FollowersParams extends PaginationParams {
  search?: string;
}

// =============================================================================
// FOLLOW
// =============================================================================

export async function createFollowApi(
  data: CreateFollowData,
): Promise<{ transaction_id: string; status: string }> {
  const response = await apiClient.post("/network/follow/", data);
  return response.data;
}

export async function unfollowApi(followId: string): Promise<void> {
  await apiClient.delete(`/network/follow/${followId}/`);
}

export async function fetchFollowingApi(
  params?: FollowingParams,
): Promise<PaginatedResponse<FollowingItem>> {
  const response = await apiClient.get<PaginatedResponse<FollowingItem>>(
    "/network/following/",
    { params },
  );
  return response.data;
}

// =============================================================================
// USER CONNECTIONS
// =============================================================================

export async function createConnectionRequestApi(
  data: CreateConnectionData,
): Promise<{ transaction_id: string; status: string }> {
  const response = await apiClient.post("/network/connections/request/", data);
  return response.data;
}

export async function disconnectUserApi(connectionId: string): Promise<void> {
  await apiClient.delete(`/network/connections/${connectionId}/`);
}

export async function fetchConnectionsApi(
  params?: ConnectionsParams,
): Promise<PaginatedResponse<UserConnectionItem>> {
  const response = await apiClient.get<PaginatedResponse<UserConnectionItem>>(
    "/network/connections/",
    { params },
  );
  return response.data;
}

// =============================================================================
// BUSINESS FOLLOWERS
// =============================================================================

export async function fetchBusinessFollowersApi(
  slug: string,
  params?: FollowersParams,
): Promise<PaginatedResponse<FollowerItem>> {
  const response = await apiClient.get<PaginatedResponse<FollowerItem>>(
    `/network/business/${slug}/followers/`,
    { params },
  );
  return response.data;
}

export async function removeBusinessFollowerApi(
  slug: string,
  followId: string,
): Promise<void> {
  await apiClient.delete(`/network/business/${slug}/followers/${followId}/`);
}

// =============================================================================
// BUSINESS CONNECTIONS
// =============================================================================

export async function createBusinessConnectionApi(
  slug: string,
  data: CreateBusinessConnectionData,
): Promise<{ transaction_id: string; status: string }> {
  const response = await apiClient.post(
    `/network/business/${slug}/connections/request/`,
    data,
  );
  return response.data;
}

export async function disconnectBusinessConnectionApi(
  slug: string,
  connectionId: string,
): Promise<void> {
  await apiClient.delete(
    `/network/business/${slug}/connections/${connectionId}/`,
  );
}

export async function fetchBusinessConnectionsApi(
  slug: string,
  params?: ConnectionsParams,
): Promise<PaginatedResponse<AccountConnectionItem>> {
  const response = await apiClient.get<PaginatedResponse<AccountConnectionItem>>(
    `/network/business/${slug}/connections/`,
    { params },
  );
  return response.data;
}

// =============================================================================
// STATS
// =============================================================================

export async function fetchNetworkStatsApi(): Promise<NetworkStats> {
  const response = await apiClient.get<NetworkStats>("/network/stats/");
  return response.data;
}

export async function fetchBusinessNetworkStatsApi(
  slug: string,
): Promise<NetworkStats> {
  const response = await apiClient.get<NetworkStats>(
    `/network/business/${slug}/stats/`,
  );
  return response.data;
}
