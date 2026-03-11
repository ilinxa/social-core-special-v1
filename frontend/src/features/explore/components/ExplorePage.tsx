"use client";

import { useCallback, useMemo } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { useIsAuthenticated } from "@/stores/auth-store";
import type { BusinessSearchParams, UserSearchParams } from "@/types/explore";
import { AllTabContent } from "./AllTabContent";
import { BusinessSearchContent } from "./BusinessSearchContent";
import type { ExploreTab } from "./ExploreTabs";
import { ExploreTabs } from "./ExploreTabs";
import { FilterPanel } from "./FilterPanel";
import { SearchBar } from "./SearchBar";
import { UserSearchContent } from "./UserSearchContent";

export function ExplorePage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const isAuthenticated = useIsAuthenticated();

  // Read URL state
  const activeTab = (searchParams.get("tab") as ExploreTab) || "all";
  const query = searchParams.get("q") ?? "";

  // Build filter params from URL (page is managed by infinite scroll, not URL)
  const businessParams = useMemo<Omit<BusinessSearchParams, "page">>(() => {
    const p: Omit<BusinessSearchParams, "page"> = {};
    if (query) p.q = query;
    const fields = [
      "country",
      "city",
      "industry",
      "company_size",
      "business_type",
      "verified",
      "is_platform_branch",
      "tags",
      "founded_year_min",
      "founded_year_max",
      "has_website",
      "ordering",
    ] as const;
    for (const field of fields) {
      const val = searchParams.get(field);
      if (val) (p as Record<string, string>)[field] = val;
    }
    return p;
  }, [query, searchParams]);

  const userParams = useMemo<Omit<UserSearchParams, "page">>(() => {
    const p: Omit<UserSearchParams, "page"> = {};
    if (query) p.q = query;
    const fields = ["country", "city", "language", "verified", "tags", "ordering"] as const;
    for (const field of fields) {
      const val = searchParams.get(field);
      if (val) (p as Record<string, string>)[field] = val;
    }
    return p;
  }, [query, searchParams]);

  // Update URL helper
  const updateUrl = useCallback(
    (updates: Record<string, string | undefined>) => {
      const params = new URLSearchParams(searchParams.toString());
      for (const [key, value] of Object.entries(updates)) {
        if (value === undefined || value === "") {
          params.delete(key);
        } else {
          params.set(key, value);
        }
      }
      router.replace(`/explore?${params.toString()}`, { scroll: false });
    },
    [router, searchParams],
  );

  const handleQueryChange = useCallback(
    (q: string) => {
      updateUrl({ q: q || undefined });
    },
    [updateUrl],
  );

  const handleTabChange = useCallback(
    (tab: ExploreTab) => {
      // Keep query, reset filters and page on tab switch
      const params = new URLSearchParams();
      if (tab !== "all") params.set("tab", tab);
      if (query) params.set("q", query);
      const qs = params.toString();
      router.replace(`/explore${qs ? `?${qs}` : ""}`, { scroll: false });
    },
    [router, query],
  );

  const handleBusinessFilterChange = useCallback(
    (updates: Partial<BusinessSearchParams>) => {
      const mapped: Record<string, string | undefined> = {};
      for (const [key, value] of Object.entries(updates)) {
        mapped[key] = value === undefined || value === null ? undefined : String(value);
      }
      updateUrl(mapped);
    },
    [updateUrl],
  );

  const handleUserFilterChange = useCallback(
    (updates: Partial<UserSearchParams>) => {
      const mapped: Record<string, string | undefined> = {};
      for (const [key, value] of Object.entries(updates)) {
        mapped[key] = value === undefined || value === null ? undefined : String(value);
      }
      updateUrl(mapped);
    },
    [updateUrl],
  );

  return (
    <div className="mx-auto max-w-5xl space-y-6 p-4 md:p-6">
      <div>
        <h1 className="text-2xl font-bold">Explore</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Discover businesses and connect with people
        </p>
      </div>

      {/* Search */}
      <SearchBar value={query} onChange={handleQueryChange} />

      {/* Tabs */}
      <ExploreTabs
        activeTab={activeTab}
        onTabChange={handleTabChange}
        showUsersTab={isAuthenticated}
      />

      {/* Filters */}
      <FilterPanel
        activeTab={activeTab}
        businessParams={businessParams}
        userParams={userParams}
        onBusinessChange={handleBusinessFilterChange}
        onUserChange={handleUserFilterChange}
      />

      {/* Results */}
      {activeTab === "all" && (
        <AllTabContent query={query} isAuthenticated={isAuthenticated} />
      )}
      {activeTab === "businesses" && (
        <BusinessSearchContent params={businessParams} />
      )}
      {activeTab === "users" && isAuthenticated && (
        <UserSearchContent params={userParams} />
      )}
    </div>
  );
}
