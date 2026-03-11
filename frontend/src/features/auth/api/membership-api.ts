import { apiClient } from "@/lib/api-client";
import type { Membership } from "@/types/rbac";

export async function fetchMyMembershipsApi(): Promise<Membership[]> {
  const response = await apiClient.get<Membership[]>("/users/me/memberships/");
  return response.data;
}
