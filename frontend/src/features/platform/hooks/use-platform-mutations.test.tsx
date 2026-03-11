import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import type { PlatformProfile } from "@/types/organization";

// =============================================================================
// MOCKS
// =============================================================================

vi.mock("@/features/platform/api/platform-api", () => ({
  updatePlatformProfileApi: vi.fn(),
}));

// =============================================================================
// IMPORTS (after mocks)
// =============================================================================

import { useUpdatePlatformProfile } from "./use-platform-mutations";
import { updatePlatformProfileApi } from "@/features/platform/api/platform-api";

// =============================================================================
// HELPERS
// =============================================================================

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

// =============================================================================
// TEST DATA
// =============================================================================

const mockProfile: PlatformProfile = {
  name: "Updated Platform",
  tagline: "Updated tagline",
  description: "Updated description",
  logo: null,
  favicon: null,
  primary_color: "#FF0000",
  secondary_color: "#00FF00",
  contact_email: "updated@platform.com",
  contact_phone: "+9876543210",
  address: "456 Oak Ave",
  social_links: {},
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-02T00:00:00Z",
};

// =============================================================================
// TESTS
// =============================================================================

beforeEach(() => {
  vi.clearAllMocks();
});

describe("useUpdatePlatformProfile", () => {
  it("calls updatePlatformProfileApi with data", async () => {
    vi.mocked(updatePlatformProfileApi).mockResolvedValue(mockProfile);

    const { result } = renderHook(() => useUpdatePlatformProfile(), {
      wrapper: createWrapper(),
    });

    const updateData = { name: "Updated Platform", tagline: "Updated tagline" };
    result.current.mutate(updateData);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(updatePlatformProfileApi).toHaveBeenCalledTimes(1);
    expect(updatePlatformProfileApi).toHaveBeenCalledWith(updateData);
  });

  it("invalidates platform account query on success", async () => {
    vi.mocked(updatePlatformProfileApi).mockResolvedValue(mockProfile);

    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    function Wrapper({ children }: { children: React.ReactNode }) {
      return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
    }

    const { result } = renderHook(() => useUpdatePlatformProfile(), {
      wrapper: Wrapper,
    });

    result.current.mutate({ name: "New Name" });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ["platform", "account"],
    });
  });

  it("sets isError on API failure", async () => {
    vi.mocked(updatePlatformProfileApi).mockRejectedValue(new Error("Server error"));

    const { result } = renderHook(() => useUpdatePlatformProfile(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({ name: "Fail" });

    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(result.current.error).toBeInstanceOf(Error);
    expect(result.current.error?.message).toBe("Server error");
  });
});
