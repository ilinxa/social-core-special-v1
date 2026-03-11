import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { useCityData, useCountryOptions, useCitiesForCountry } from "./use-city-data";

// =============================================================================
// MOCKS
// =============================================================================

const mockCityData: Record<string, string[]> = {
  US: ["New York", "San Francisco", "Los Angeles"],
  GB: ["London", "Manchester"],
};

beforeEach(() => {
  vi.clearAllMocks();
  vi.stubGlobal("fetch", vi.fn());
});

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
// TESTS
// =============================================================================

describe("useCityData", () => {
  it("fetches and returns city data", async () => {
    vi.mocked(fetch).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockCityData),
    } as Response);

    const { result } = renderHook(() => useCityData(), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual(mockCityData);
    expect(fetch).toHaveBeenCalledWith("/data/cities.json");
  });

  it("uses Infinity staleTime", async () => {
    vi.mocked(fetch).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockCityData),
    } as Response);

    const { result } = renderHook(() => useCityData(), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    // Data was fetched exactly once — Infinity staleTime means no refetch
    expect(fetch).toHaveBeenCalledTimes(1);
  });
});

describe("useCountryOptions", () => {
  it("returns sorted country codes when data is loaded", async () => {
    vi.mocked(fetch).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockCityData),
    } as Response);

    const { result } = renderHook(() => useCountryOptions(), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current.length).toBeGreaterThan(0));

    expect(result.current).toEqual(["GB", "US"]);
  });

  it("returns empty array before data is loaded", () => {
    vi.mocked(fetch).mockReturnValue(new Promise(() => {})); // never resolves

    const { result } = renderHook(() => useCountryOptions(), { wrapper: createWrapper() });

    expect(result.current).toEqual([]);
  });
});

describe("useCitiesForCountry", () => {
  it("returns cities for a given country", async () => {
    vi.mocked(fetch).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockCityData),
    } as Response);

    const { result } = renderHook(() => useCitiesForCountry("US"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.length).toBeGreaterThan(0));

    expect(result.current).toEqual(["New York", "San Francisco", "Los Angeles"]);
  });

  it("returns empty array for unknown country", async () => {
    vi.mocked(fetch).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockCityData),
    } as Response);

    const { result } = renderHook(() => useCitiesForCountry("XX"), {
      wrapper: createWrapper(),
    });

    // Wait for data to load
    await waitFor(() => {
      const { result: cityResult } = renderHook(() => useCityData(), { wrapper: createWrapper() });
      return cityResult.current.data !== undefined;
    });

    expect(result.current).toEqual([]);
  });

  it("returns empty array when country is empty string", () => {
    vi.mocked(fetch).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockCityData),
    } as Response);

    const { result } = renderHook(() => useCitiesForCountry(""), {
      wrapper: createWrapper(),
    });

    expect(result.current).toEqual([]);
  });
});
