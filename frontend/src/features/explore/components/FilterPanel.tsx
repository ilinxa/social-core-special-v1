"use client";

import { ChevronDown } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import type { BusinessSearchParams, UserSearchParams } from "@/types/explore";
import type { ExploreTab } from "./ExploreTabs";
import { BusinessFilters } from "./BusinessFilters";
import { UserFilters } from "./UserFilters";

interface FilterPanelProps {
  activeTab: ExploreTab;
  businessParams: Omit<BusinessSearchParams, "page">;
  userParams: Omit<UserSearchParams, "page">;
  onBusinessChange: (updates: Partial<BusinessSearchParams>) => void;
  onUserChange: (updates: Partial<UserSearchParams>) => void;
}

export function FilterPanel({
  activeTab,
  businessParams,
  userParams,
  onBusinessChange,
  onUserChange,
}: FilterPanelProps) {
  const [open, setOpen] = useState(false);

  // No filters on "all" tab
  if (activeTab === "all") return null;

  const hasActiveFilters =
    activeTab === "businesses"
      ? !!(
          businessParams.country ||
          businessParams.city ||
          businessParams.industry ||
          businessParams.company_size ||
          businessParams.business_type ||
          businessParams.verified ||
          businessParams.is_platform_branch ||
          businessParams.tags ||
          businessParams.founded_year_min ||
          businessParams.founded_year_max ||
          businessParams.has_website
        )
      : !!(
          userParams.country ||
          userParams.city ||
          userParams.language ||
          userParams.verified ||
          userParams.tags
        );

  return (
    <div>
      {/* Toggle button — full width */}
      <Button
        variant="outline"
        size="sm"
        onClick={() => setOpen((v) => !v)}
        className="w-full justify-between gap-1.5"
      >
        <span className="flex items-center gap-1.5">
          Filters
          {hasActiveFilters && (
            <span className="flex h-4 w-4 items-center justify-center rounded-full bg-primary text-[10px] font-medium text-primary-foreground">
              !
            </span>
          )}
        </span>
        <ChevronDown
          className={`h-3.5 w-3.5 transition-transform ${open ? "rotate-180" : ""}`}
        />
      </Button>

      {/* Collapsible filter area */}
      <div
        className={`grid transition-[grid-template-rows] duration-200 ${
          open ? "grid-rows-[1fr]" : "grid-rows-[0fr]"
        }`}
      >
        <div className="overflow-hidden">
          <div className="pt-4">
            {activeTab === "businesses" ? (
              <BusinessFilters params={businessParams} onChange={onBusinessChange} />
            ) : (
              <UserFilters params={userParams} onChange={onUserChange} />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
