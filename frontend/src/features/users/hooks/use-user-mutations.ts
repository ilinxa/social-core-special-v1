import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { queryKeys } from "@/lib/query-keys";
import { useAuthStore } from "@/stores/auth-store";
import {
  deactivateAccountApi,
  deleteAvatarApi,
  deleteCoverImageApi,
  fetchCurrentUserApi,
  updateProfileApi,
  updateUsernameApi,
  uploadAvatarApi,
  uploadCoverImageApi,
} from "@/features/users/api/users-api";

// =============================================================================
// USERNAME MUTATION
// =============================================================================

export function useUpdateUsername() {
  const queryClient = useQueryClient();
  const setUser = useAuthStore((s) => s.setUser);

  return useMutation({
    mutationFn: updateUsernameApi,
    onSuccess: (updatedUser) => {
      setUser(updatedUser);
      queryClient.setQueryData(queryKeys.users.me(), updatedUser);
      toast.success("Username updated");
    },
  });
}

// =============================================================================
// PROFILE MUTATION
// =============================================================================

export function useUpdateProfile() {
  const queryClient = useQueryClient();
  const setUser = useAuthStore((s) => s.setUser);

  return useMutation({
    mutationFn: updateProfileApi,
    onSuccess: async (updatedProfile) => {
      queryClient.setQueryData(queryKeys.users.profile(), updatedProfile);
      try {
        const freshUser = await fetchCurrentUserApi();
        setUser(freshUser);
        queryClient.setQueryData(queryKeys.users.me(), freshUser);
      } catch {
        queryClient.invalidateQueries({ queryKey: queryKeys.users.me() });
      }
      toast.success("Profile updated");
    },
  });
}

// =============================================================================
// AVATAR MUTATIONS
// =============================================================================

export function useUploadAvatar() {
  const queryClient = useQueryClient();
  const setUser = useAuthStore((s) => s.setUser);

  return useMutation({
    mutationFn: uploadAvatarApi,
    onSuccess: async () => {
      toast.success("Avatar updated");
      try {
        const freshUser = await fetchCurrentUserApi();
        setUser(freshUser);
        queryClient.setQueryData(queryKeys.users.me(), freshUser);
        queryClient.setQueryData(queryKeys.users.profile(), freshUser.profile);
      } catch {
        queryClient.invalidateQueries({ queryKey: queryKeys.users.me() });
      }
    },
  });
}

export function useDeleteAvatar() {
  const queryClient = useQueryClient();
  const setUser = useAuthStore((s) => s.setUser);

  return useMutation({
    mutationFn: deleteAvatarApi,
    onSuccess: async () => {
      toast.success("Avatar removed");
      try {
        const freshUser = await fetchCurrentUserApi();
        setUser(freshUser);
        queryClient.setQueryData(queryKeys.users.me(), freshUser);
        queryClient.setQueryData(queryKeys.users.profile(), freshUser.profile);
      } catch {
        queryClient.invalidateQueries({ queryKey: queryKeys.users.me() });
      }
    },
  });
}

// =============================================================================
// COVER IMAGE MUTATIONS
// =============================================================================

export function useUploadCoverImage() {
  const queryClient = useQueryClient();
  const setUser = useAuthStore((s) => s.setUser);

  return useMutation({
    mutationFn: uploadCoverImageApi,
    onSuccess: async () => {
      toast.success("Cover image updated");
      try {
        const freshUser = await fetchCurrentUserApi();
        setUser(freshUser);
        queryClient.setQueryData(queryKeys.users.me(), freshUser);
        queryClient.setQueryData(queryKeys.users.profile(), freshUser.profile);
      } catch {
        queryClient.invalidateQueries({ queryKey: queryKeys.users.me() });
      }
    },
  });
}

export function useDeleteCoverImage() {
  const queryClient = useQueryClient();
  const setUser = useAuthStore((s) => s.setUser);

  return useMutation({
    mutationFn: deleteCoverImageApi,
    onSuccess: async () => {
      toast.success("Cover image removed");
      try {
        const freshUser = await fetchCurrentUserApi();
        setUser(freshUser);
        queryClient.setQueryData(queryKeys.users.me(), freshUser);
        queryClient.setQueryData(queryKeys.users.profile(), freshUser.profile);
      } catch {
        queryClient.invalidateQueries({ queryKey: queryKeys.users.me() });
      }
    },
  });
}

// =============================================================================
// ACCOUNT DEACTIVATION
// =============================================================================

export function useDeactivateAccount() {
  const logout = useAuthStore((s) => s.logout);

  return useMutation({
    mutationFn: deactivateAccountApi,
    onSuccess: () => {
      toast.success("Account deactivated");
      logout();
    },
  });
}
