import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import type { BusinessProfile } from "@/types/organization";

// =============================================================================
// MOCKS
// =============================================================================

vi.mock("@/features/business/api/business-api", () => ({
  updateBusinessProfileApi: vi.fn(),
}));

// =============================================================================
// IMPORTS (after mocks)
// =============================================================================

import { useUpdateBusinessProfile } from "./use-business-mutations";
import { updateBusinessProfileApi } from "@/features/business/api/business-api";

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

const mockProfile: BusinessProfile = {
  display_name: "Updated Name",
  tagline: "Updated tagline",
  description: "Updated description",
  logo: null,
  cover_image: null,
  website: "https://updated.com",
  contact_email: "updated@example.com",
  contact_phone: "+9876543210",
  industry: "Finance",
  company_size: "201-500",
  founded_year: 2015,
  social_links: {},
  tags: [],
  is_public: true,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-02T00:00:00Z",
};

// =============================================================================
// TESTS
// =============================================================================

beforeEach(() => {
  vi.clearAllMocks();
});

describe("useUpdateBusinessProfile", () => {
  it("calls updateBusinessProfileApi with slug and data", async () => {
    vi.mocked(updateBusinessProfileApi).mockResolvedValue(mockProfile);

    const { result } = renderHook(() => useUpdateBusinessProfile("acme"), {
      wrapper: createWrapper(),
    });

    const updateData = { display_name: "Updated Name", tagline: "Updated tagline" };
    result.current.mutate(updateData);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(updateBusinessProfileApi).toHaveBeenCalledTimes(1);
    expect(updateBusinessProfileApi).toHaveBeenCalledWith("acme", updateData);
  });

  it("invalidates business detail query on success", async () => {
    vi.mocked(updateBusinessProfileApi).mockResolvedValue(mockProfile);

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

    const { result } = renderHook(() => useUpdateBusinessProfile("acme"), {
      wrapper: Wrapper,
    });

    result.current.mutate({ display_name: "New Name" });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ["business", "detail", "acme"],
    });
  });

  it("sets isError on API failure", async () => {
    vi.mocked(updateBusinessProfileApi).mockRejectedValue(new Error("Network error"));

    const { result } = renderHook(() => useUpdateBusinessProfile("acme"), {
      wrapper: createWrapper(),
    });

    result.current.mutate({ display_name: "Fail" });

    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(result.current.error).toBeInstanceOf(Error);
    expect(result.current.error?.message).toBe("Network error");
  });
});
