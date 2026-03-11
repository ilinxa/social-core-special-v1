"use client";

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import type { BusinessSearchParams } from "@/types/explore";
import { CountrySelect } from "./CountrySelect";
import { CityCombobox } from "./CityCombobox";
import { TagInput } from "./TagInput";

interface BusinessFiltersProps {
  params: Omit<BusinessSearchParams, "page">;
  onChange: (updates: Partial<BusinessSearchParams>) => void;
}

// Matches backend CompanySize TextChoices exactly
const COMPANY_SIZES = [
  { value: "1", label: "1 employee" },
  { value: "2-10", label: "2-10" },
  { value: "11-50", label: "11-50" },
  { value: "51-200", label: "51-200" },
  { value: "201-500", label: "201-500" },
  { value: "500+", label: "500+" },
];

// Matches backend BusinessType TextChoices exactly
const BUSINESS_TYPES = [
  { value: "sole_proprietorship", label: "Sole Proprietorship" },
  { value: "partnership", label: "Partnership" },
  { value: "llc", label: "LLC" },
  { value: "corporation", label: "Corporation" },
  { value: "nonprofit", label: "Nonprofit" },
  { value: "cooperative", label: "Cooperative" },
  { value: "other", label: "Other" },
];

// Free-text on backend, but common values for convenience
const INDUSTRIES = [
  "Technology",
  "Healthcare",
  "Finance",
  "Education",
  "Retail",
  "Manufacturing",
  "Real Estate",
  "Marketing",
  "Consulting",
  "Food & Beverage",
];

const ORDERING_OPTIONS = [
  { value: "relevance", label: "Relevance" },
  { value: "name", label: "Name" },
  { value: "newest", label: "Newest" },
];

export function BusinessFilters({ params, onChange }: BusinessFiltersProps) {
  return (
    <div className="space-y-3 rounded-lg border bg-muted/40 p-4">
      {/* Row 1: Location + Type filters */}
      <div className="flex flex-wrap items-end gap-x-4 gap-y-3">
        {/* Country */}
        <div className="w-40 space-y-1">
          <Label htmlFor="biz-country" className="text-xs">
            Country
          </Label>
          <CountrySelect
            id="biz-country"
            value={params.country ?? ""}
            onChange={(v) => onChange({ country: v || undefined, city: undefined })}
          />
        </div>

        {/* City (cascading — depends on country) */}
        <div className="w-40 space-y-1">
          <Label htmlFor="biz-city" className="text-xs">
            City
          </Label>
          <CityCombobox
            id="biz-city"
            country={params.country ?? ""}
            value={params.city ?? ""}
            onChange={(v) => onChange({ city: v || undefined })}
          />
        </div>

        {/* Industry */}
        <div className="w-40 space-y-1">
          <Label htmlFor="industry" className="text-xs">
            Industry
          </Label>
          <Select
            value={params.industry ?? "all"}
            onValueChange={(v) => onChange({ industry: v === "all" ? undefined : v })}
          >
            <SelectTrigger id="industry" className="h-8 text-xs">
              <SelectValue placeholder="All industries" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All industries</SelectItem>
              {INDUSTRIES.map((ind) => (
                <SelectItem key={ind} value={ind}>
                  {ind}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Business Type */}
        <div className="w-44 space-y-1">
          <Label htmlFor="business-type" className="text-xs">
            Business Type
          </Label>
          <Select
            value={params.business_type ?? "all"}
            onValueChange={(v) =>
              onChange({ business_type: v === "all" ? undefined : v })
            }
          >
            <SelectTrigger id="business-type" className="h-8 text-xs">
              <SelectValue placeholder="All types" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All types</SelectItem>
              {BUSINESS_TYPES.map((bt) => (
                <SelectItem key={bt.value} value={bt.value}>
                  {bt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Company Size */}
        <div className="w-36 space-y-1">
          <Label htmlFor="company-size" className="text-xs">
            Company Size
          </Label>
          <Select
            value={params.company_size ?? "all"}
            onValueChange={(v) =>
              onChange({ company_size: v === "all" ? undefined : v })
            }
          >
            <SelectTrigger id="company-size" className="h-8 text-xs">
              <SelectValue placeholder="All sizes" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All sizes</SelectItem>
              {COMPANY_SIZES.map((size) => (
                <SelectItem key={size.value} value={size.value}>
                  {size.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Row 2: Founded year + Tags + Sort + Toggles */}
      <div className="flex flex-wrap items-end gap-x-4 gap-y-3">
        {/* Founded Year Range */}
        <div className="space-y-1">
          <Label className="text-xs">Founded Year</Label>
          <div className="flex items-center gap-1.5">
            <Input
              type="number"
              placeholder="From"
              className="h-8 w-20 text-xs"
              value={params.founded_year_min ?? ""}
              onChange={(e) =>
                onChange({ founded_year_min: e.target.value || undefined })
              }
            />
            <span className="text-xs text-muted-foreground">-</span>
            <Input
              type="number"
              placeholder="To"
              className="h-8 w-20 text-xs"
              value={params.founded_year_max ?? ""}
              onChange={(e) =>
                onChange({ founded_year_max: e.target.value || undefined })
              }
            />
          </div>
        </div>

        {/* Tags */}
        <div className="min-w-48 max-w-72 flex-1 space-y-1">
          <Label className="text-xs">Tags</Label>
          <TagInput
            value={params.tags ?? ""}
            onChange={(v) => onChange({ tags: v || undefined })}
            category="business"
          />
        </div>

        {/* Ordering */}
        <div className="w-32 space-y-1">
          <Label htmlFor="ordering" className="text-xs">
            Sort by
          </Label>
          <Select
            value={params.ordering ?? "relevance"}
            onValueChange={(v) => onChange({ ordering: v })}
          >
            <SelectTrigger id="ordering" className="h-8 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {ORDERING_OPTIONS.map((opt) => (
                <SelectItem key={opt.value} value={opt.value}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Divider */}
        <div className="hidden h-8 w-px bg-border sm:block" />

        {/* Verified toggle */}
        <div className="flex items-center gap-2">
          <Switch
            id="verified"
            checked={params.verified === "true"}
            onCheckedChange={(checked) =>
              onChange({ verified: checked ? "true" : undefined })
            }
          />
          <Label htmlFor="verified" className="text-xs">
            Verified
          </Label>
        </div>

        {/* Has website toggle */}
        <div className="flex items-center gap-2">
          <Switch
            id="has-website"
            checked={params.has_website === "true"}
            onCheckedChange={(checked) =>
              onChange({ has_website: checked ? "true" : undefined })
            }
          />
          <Label htmlFor="has-website" className="text-xs">
            Has website
          </Label>
        </div>
      </div>
    </div>
  );
}
