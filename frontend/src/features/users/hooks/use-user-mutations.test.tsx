import { vi, describe, it, expect, beforeEach } from "vitest";

const mockSetUser = vi.fn();

vi.mock("@/stores/auth-store", () => ({
  useAuthStore: (selector: (s: Record<string, unknown>) => unknown) =>
    selector({ setUser: mockSetUser }),
}));

vi.mock("sonner", () => ({
  toast: { success: vi.fn() },
}));

vi.mock("@/features/users/api/users-api");

import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { toast } from "sonner";

import { queryKeys } from "@/lib/query-keys";
import {
  deleteAvatarApi,
  fetchCurrentUserApi,
  updateProfileApi,
  updateUsernameApi,
  uploadAvatarApi,
} from "@/features/users/api/users-api";
import type { User } from "@/types/auth";
import {
  useUpdateUsername,
  useUpdateProfile,
  useUploadAvatar,
  useDeleteAvatar,
} from "./use-user-mutations";

const mockUser: User = {
  id: "550e8400-e29b-41d4-a716-446655440000",
  email: "test@example.com",
  username: "testuser",
  is_active: true,
  is_verified: true,
  is_complete: true,
  can_create_business: true,
  is_staff: false,
  is_superuser: false,
  date_joined: "2026-01-01T00:00:00Z",
  last_login: null,
  profile: {
    first_name: "Test",
    last_name: "User",
    full_name: "Test User",
    display_name: "testuser",
    phone: "",
    avatar_url: null,
    has_avatar: false,
    timezone: "UTC",
    language: "en",
    bio: "",
    country: "",
    city: "",
    tags: [],
    is_public: true,
  },
};

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("useUpdateUsername", () => {
  it("calls updateUsernameApi with correct args", async () => {
    vi.mocked(updateUsernameApi).mockResolvedValue(mockUser);

    const { result } = renderHook(() => useUpdateUsername(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({ username: "newuser" });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(vi.mocked(updateUsernameApi).mock.calls[0][0]).toEqual({ username: "newuser" });
  });

  it("sets user in auth store on success", async () => {
    vi.mocked(updateUsernameApi).mockResolvedValue(mockUser);

    const { result } = renderHook(() => useUpdateUsername(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({ username: "newuser" });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockSetUser).toHaveBeenCalledWith(mockUser);
  });

  it("sets query data for users.me() key", async () => {
    vi.mocked(updateUsernameApi).mockResolvedValue(mockUser);

    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
    const setQueryDataSpy = vi.spyOn(queryClient, "setQueryData");

    function Wrapper({ children }: { children: React.ReactNode }) {
      return (
        <QueryClientProvider client={queryClient}>
          {children}
        </QueryClientProvider>
      );
    }

    const { result } = renderHook(() => useUpdateUsername(), {
      wrapper: Wrapper,
    });

    result.current.mutate({ username: "newuser" });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(setQueryDataSpy).toHaveBeenCalledWith(
      queryKeys.users.me(),
      mockUser,
    );
  });

  it('shows "Username updated" toast', async () => {
    vi.mocked(updateUsernameApi).mockResolvedValue(mockUser);

    const { result } = renderHook(() => useUpdateUsername(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({ username: "newuser" });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(toast.success).toHaveBeenCalledWith("Username updated");
  });
});

describe("useUpdateProfile", () => {
  const mockProfile = mockUser.profile;

  it("calls updateProfileApi with correct args", async () => {
    vi.mocked(updateProfileApi).mockResolvedValue(mockProfile);
    vi.mocked(fetchCurrentUserApi).mockResolvedValue(mockUser);

    const { result } = renderHook(() => useUpdateProfile(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({ first_name: "Updated" });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(vi.mocked(updateProfileApi).mock.calls[0][0]).toEqual({ first_name: "Updated" });
  });

  it("sets query data for users.profile() key", async () => {
    vi.mocked(updateProfileApi).mockResolvedValue(mockProfile);
    vi.mocked(fetchCurrentUserApi).mockResolvedValue(mockUser);

    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
    const setQueryDataSpy = vi.spyOn(queryClient, "setQueryData");

    function Wrapper({ children }: { children: React.ReactNode }) {
      return (
        <QueryClientProvider client={queryClient}>
          {children}
        </QueryClientProvider>
      );
    }

    const { result } = renderHook(() => useUpdateProfile(), {
      wrapper: Wrapper,
    });

    result.current.mutate({ first_name: "Updated" });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(setQueryDataSpy).toHaveBeenCalledWith(
      queryKeys.users.profile(),
      mockProfile,
    );
  });

  it("fetches fresh user and updates auth store", async () => {
    vi.mocked(updateProfileApi).mockResolvedValue(mockProfile);
    vi.mocked(fetchCurrentUserApi).mockResolvedValue(mockUser);

    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
    const setQueryDataSpy = vi.spyOn(queryClient, "setQueryData");

    function Wrapper({ children }: { children: React.ReactNode }) {
      return (
        <QueryClientProvider client={queryClient}>
          {children}
        </QueryClientProvider>
      );
    }

    const { result } = renderHook(() => useUpdateProfile(), {
      wrapper: Wrapper,
    });

    result.current.mutate({ first_name: "Updated" });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(fetchCurrentUserApi).toHaveBeenCalled();
    expect(mockSetUser).toHaveBeenCalledWith(mockUser);
    expect(setQueryDataSpy).toHaveBeenCalledWith(
      queryKeys.users.me(),
      mockUser,
    );
  });

  it('shows "Profile updated" toast', async () => {
    vi.mocked(updateProfileApi).mockResolvedValue(mockProfile);
    vi.mocked(fetchCurrentUserApi).mockResolvedValue(mockUser);

    const { result } = renderHook(() => useUpdateProfile(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({ first_name: "Updated" });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(toast.success).toHaveBeenCalledWith("Profile updated");
  });

  it("falls back to invalidateQueries if fetchCurrentUserApi fails", async () => {
    vi.mocked(updateProfileApi).mockResolvedValue(mockProfile);
    vi.mocked(fetchCurrentUserApi).mockRejectedValue(new Error("fail"));

    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    function Wrapper({ children }: { children: React.ReactNode }) {
      return (
        <QueryClientProvider client={queryClient}>
          {children}
        </QueryClientProvider>
      );
    }

    const { result } = renderHook(() => useUpdateProfile(), {
      wrapper: Wrapper,
    });

    result.current.mutate({ first_name: "Updated" });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: queryKeys.users.me(),
    });
  });
});

describe("useUploadAvatar", () => {
  it("calls uploadAvatarApi", async () => {
    const file = new File(["avatar"], "avatar.png", { type: "image/png" });
    vi.mocked(uploadAvatarApi).mockResolvedValue(undefined as never);
    vi.mocked(fetchCurrentUserApi).mockResolvedValue(mockUser);

    const { result } = renderHook(() => useUploadAvatar(), {
      wrapper: createWrapper(),
    });

    result.current.mutate(file);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(vi.mocked(uploadAvatarApi).mock.calls[0][0]).toEqual(file);
  });

  it('shows "Avatar updated" toast', async () => {
    const file = new File(["avatar"], "avatar.png", { type: "image/png" });
    vi.mocked(uploadAvatarApi).mockResolvedValue(undefined as never);
    vi.mocked(fetchCurrentUserApi).mockResolvedValue(mockUser);

    const { result } = renderHook(() => useUploadAvatar(), {
      wrapper: createWrapper(),
    });

    result.current.mutate(file);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(toast.success).toHaveBeenCalledWith("Avatar updated");
  });

  it("fetches fresh user and updates both me and profile query data", async () => {
    const file = new File(["avatar"], "avatar.png", { type: "image/png" });
    vi.mocked(uploadAvatarApi).mockResolvedValue(undefined as never);
    vi.mocked(fetchCurrentUserApi).mockResolvedValue(mockUser);

    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
    const setQueryDataSpy = vi.spyOn(queryClient, "setQueryData");

    function Wrapper({ children }: { children: React.ReactNode }) {
      return (
        <QueryClientProvider client={queryClient}>
          {children}
        </QueryClientProvider>
      );
    }

    const { result } = renderHook(() => useUploadAvatar(), {
      wrapper: Wrapper,
    });

    result.current.mutate(file);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(fetchCurrentUserApi).toHaveBeenCalled();
    expect(mockSetUser).toHaveBeenCalledWith(mockUser);
    expect(setQueryDataSpy).toHaveBeenCalledWith(
      queryKeys.users.me(),
      mockUser,
    );
    expect(setQueryDataSpy).toHaveBeenCalledWith(
      queryKeys.users.profile(),
      mockUser.profile,
    );
  });

  it("falls back to invalidateQueries if fetchCurrentUserApi fails", async () => {
    const file = new File(["avatar"], "avatar.png", { type: "image/png" });
    vi.mocked(uploadAvatarApi).mockResolvedValue(undefined as never);
    vi.mocked(fetchCurrentUserApi).mockRejectedValue(new Error("fail"));

    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    function Wrapper({ children }: { children: React.ReactNode }) {
      return (
        <QueryClientProvider client={queryClient}>
          {children}
        </QueryClientProvider>
      );
    }

    const { result } = renderHook(() => useUploadAvatar(), {
      wrapper: Wrapper,
    });

    result.current.mutate(file);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: queryKeys.users.me(),
    });
  });
});

describe("useDeleteAvatar", () => {
  it("calls deleteAvatarApi", async () => {
    vi.mocked(deleteAvatarApi).mockResolvedValue(undefined as never);
    vi.mocked(fetchCurrentUserApi).mockResolvedValue(mockUser);

    const { result } = renderHook(() => useDeleteAvatar(), {
      wrapper: createWrapper(),
    });

    result.current.mutate();

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(deleteAvatarApi).toHaveBeenCalled();
  });

  it('shows "Avatar removed" toast', async () => {
    vi.mocked(deleteAvatarApi).mockResolvedValue(undefined as never);
    vi.mocked(fetchCurrentUserApi).mockResolvedValue(mockUser);

    const { result } = renderHook(() => useDeleteAvatar(), {
      wrapper: createWrapper(),
    });

    result.current.mutate();

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(toast.success).toHaveBeenCalledWith("Avatar removed");
  });

  it("fetches fresh user and updates both me and profile query data", async () => {
    vi.mocked(deleteAvatarApi).mockResolvedValue(undefined as never);
    vi.mocked(fetchCurrentUserApi).mockResolvedValue(mockUser);

    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
    const setQueryDataSpy = vi.spyOn(queryClient, "setQueryData");

    function Wrapper({ children }: { children: React.ReactNode }) {
      return (
        <QueryClientProvider client={queryClient}>
          {children}
        </QueryClientProvider>
      );
    }

    const { result } = renderHook(() => useDeleteAvatar(), {
      wrapper: Wrapper,
    });

    result.current.mutate();

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(fetchCurrentUserApi).toHaveBeenCalled();
    expect(mockSetUser).toHaveBeenCalledWith(mockUser);
    expect(setQueryDataSpy).toHaveBeenCalledWith(
      queryKeys.users.me(),
      mockUser,
    );
    expect(setQueryDataSpy).toHaveBeenCalledWith(
      queryKeys.users.profile(),
      mockUser.profile,
    );
  });

  it("falls back to invalidateQueries if fetchCurrentUserApi fails", async () => {
    vi.mocked(deleteAvatarApi).mockResolvedValue(undefined as never);
    vi.mocked(fetchCurrentUserApi).mockRejectedValue(new Error("fail"));

    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    function Wrapper({ children }: { children: React.ReactNode }) {
      return (
        <QueryClientProvider client={queryClient}>
          {children}
        </QueryClientProvider>
      );
    }

    const { result } = renderHook(() => useDeleteAvatar(), {
      wrapper: Wrapper,
    });

    result.current.mutate();

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: queryKeys.users.me(),
    });
  });
});
