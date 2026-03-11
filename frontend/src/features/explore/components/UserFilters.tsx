"use client";

import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import type { UserSearchParams } from "@/types/explore";
import { CityCombobox } from "./CityCombobox";
import { CountrySelect } from "./CountrySelect";
import { TagInput } from "./TagInput";

interface UserFiltersProps {
  params: Omit<UserSearchParams, "page">;
  onChange: (updates: Partial<UserSearchParams>) => void;
}

// Common languages — backend stores as free-text language codes
const LANGUAGES = [
  { value: "en", label: "English" },
  { value: "es", label: "Spanish" },
  { value: "fr", label: "French" },
  { value: "de", label: "German" },
  { value: "pt", label: "Portuguese" },
  { value: "zh", label: "Chinese" },
  { value: "ja", label: "Japanese" },
  { value: "ko", label: "Korean" },
  { value: "ar", label: "Arabic" },
  { value: "hi", label: "Hindi" },
  { value: "ru", label: "Russian" },
  { value: "it", label: "Italian" },
  { value: "nl", label: "Dutch" },
  { value: "tr", label: "Turkish" },
  { value: "sv", label: "Swedish" },
];

const ORDERING_OPTIONS = [
  { value: "relevance", label: "Relevance" },
  { value: "name", label: "Username" },
  { value: "newest", label: "Newest" },
];

export function UserFilters({ params, onChange }: UserFiltersProps) {
  return (
    <div className="flex flex-wrap items-end gap-x-4 gap-y-3 rounded-lg border bg-muted/40 p-4">
      {/* Country */}
      <div className="w-40 space-y-1">
        <Label htmlFor="user-country" className="text-xs">
          Country
        </Label>
        <CountrySelect
          id="user-country"
          value={params.country ?? ""}
          onChange={(v) => onChange({ country: v || undefined, city: undefined })}
        />
      </div>

      {/* City (cascading — depends on country) */}
      <div className="w-40 space-y-1">
        <Label htmlFor="user-city" className="text-xs">
          City
        </Label>
        <CityCombobox
          id="user-city"
          country={params.country ?? ""}
          value={params.city ?? ""}
          onChange={(v) => onChange({ city: v || undefined })}
        />
      </div>

      {/* Language */}
      <div className="w-36 space-y-1">
        <Label htmlFor="user-language" className="text-xs">
          Language
        </Label>
        <Select
          value={params.language ?? "all"}
          onValueChange={(v) => onChange({ language: v === "all" ? undefined : v })}
        >
          <SelectTrigger id="user-language" className="h-8 text-xs">
            <SelectValue placeholder="All languages" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All languages</SelectItem>
            {LANGUAGES.map((lang) => (
              <SelectItem key={lang.value} value={lang.value}>
                {lang.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Tags */}
      <div className="min-w-48 max-w-72 flex-1 space-y-1">
        <Label className="text-xs">Tags</Label>
        <TagInput
          value={params.tags ?? ""}
          onChange={(v) => onChange({ tags: v || undefined })}
          category="user"
        />
      </div>

      {/* Ordering */}
      <div className="w-32 space-y-1">
        <Label htmlFor="user-ordering" className="text-xs">
          Sort by
        </Label>
        <Select
          value={params.ordering ?? "relevance"}
          onValueChange={(v) => onChange({ ordering: v })}
        >
          <SelectTrigger id="user-ordering" className="h-8 text-xs">
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
          id="user-verified"
          checked={params.verified === "true"}
          onCheckedChange={(checked) =>
            onChange({ verified: checked ? "true" : undefined })
          }
        />
        <Label htmlFor="user-verified" className="text-xs">
          Verified
        </Label>
      </div>
    </div>
  );
}
