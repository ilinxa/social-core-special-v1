import { describe, it, expect, vi, beforeEach } from "vitest";

import {
  fetchExploreCombinedApi,
  searchBusinessesApi,
  searchUsersApi,
  fetchTagSuggestionsApi,
  fetchCitiesApi,
} from "./explore-api";

vi.mock("@/lib/api-client", () => ({
  apiClient: {
    get: vi.fn(),
  },
}));

import { apiClient } from "@/lib/api-client";

beforeEach(() => {
  vi.clearAllMocks();
});

describe("fetchExploreCombinedApi", () => {
  it("calls GET /explore/ with query", async () => {
    const mockData = { businesses: [], users: [], businesses_count: 0, users_count: 0 };
    vi.mocked(apiClient.get).mockResolvedValue({ data: mockData });

    const result = await fetchExploreCombinedApi({ q: "test" });

    expect(apiClient.get).toHaveBeenCalledWith("/explore/?q=test");
    expect(result).toEqual(mockData);
  });

  it("calls GET /explore/ without query when empty", async () => {
    const mockData = { businesses: [], users: [], businesses_count: 0, users_count: 0 };
    vi.mocked(apiClient.get).mockResolvedValue({ data: mockData });

    await fetchExploreCombinedApi({});

    expect(apiClient.get).toHaveBeenCalledWith("/explore/");
  });
});

describe("searchBusinessesApi", () => {
  it("calls GET /explore/businesses/ with params", async () => {
    const mockData = { count: 0, next: null, previous: null, results: [] };
    vi.mocked(apiClient.get).mockResolvedValue({ data: mockData });

    const result = await searchBusinessesApi({ q: "tech", country: "US", verified: "true" });

    expect(apiClient.get).toHaveBeenCalledWith(
      "/explore/businesses/?q=tech&country=US&verified=true",
    );
    expect(result).toEqual(mockData);
  });

  it("omits empty params", async () => {
    const mockData = { count: 0, next: null, previous: null, results: [] };
    vi.mocked(apiClient.get).mockResolvedValue({ data: mockData });

    await searchBusinessesApi({ q: "", ordering: "name" });

    expect(apiClient.get).toHaveBeenCalledWith("/explore/businesses/?ordering=name");
  });
});

describe("searchUsersApi", () => {
  it("calls GET /explore/users/ with params", async () => {
    const mockData = { count: 0, next: null, previous: null, results: [] };
    vi.mocked(apiClient.get).mockResolvedValue({ data: mockData });

    const result = await searchUsersApi({ q: "john", verified: "true" });

    expect(apiClient.get).toHaveBeenCalledWith("/explore/users/?q=john&verified=true");
    expect(result).toEqual(mockData);
  });
});

describe("fetchTagSuggestionsApi", () => {
  it("calls GET /explore/tags/ with query", async () => {
    const mockTags = [{ id: 1, name: "tech", slug: "tech", category: "both", usage_count: 5 }];
    vi.mocked(apiClient.get).mockResolvedValue({ data: mockTags });

    const result = await fetchTagSuggestionsApi("tec", "business");

    expect(apiClient.get).toHaveBeenCalledWith("/explore/tags/?q=tec&category=business");
    expect(result).toEqual(mockTags);
  });

  it("calls without params when no query", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: [] });

    await fetchTagSuggestionsApi();

    expect(apiClient.get).toHaveBeenCalledWith("/explore/tags/");
  });
});

describe("fetchCitiesApi", () => {
  it("calls GET /explore/cities/ with country", async () => {
    const mockCities = { country: "US", cities: ["New York", "Los Angeles"] };
    vi.mocked(apiClient.get).mockResolvedValue({ data: mockCities });

    const result = await fetchCitiesApi("US");

    expect(apiClient.get).toHaveBeenCalledWith("/explore/cities/?country=US");
    expect(result).toEqual(mockCities);
  });
});
