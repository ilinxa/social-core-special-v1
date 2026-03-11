"use client";

import { useCallback } from "react";
import { Plus, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const PLATFORM_OPTIONS = [
  "twitter",
  "facebook",
  "instagram",
  "linkedin",
  "youtube",
  "tiktok",
  "github",
  "website",
  "other",
] as const;

const MAX_LINKS = 10;

interface SocialLinksEditorProps {
  value: Record<string, string>;
  onChange: (links: Record<string, string>) => void;
  disabled?: boolean;
}

export function SocialLinksEditor({ value, onChange, disabled }: SocialLinksEditorProps) {
  const entries = Object.entries(value);

  const handleAdd = useCallback(() => {
    if (entries.length >= MAX_LINKS) return;
    // Find the first platform not already used
    const used = new Set(Object.keys(value));
    const nextPlatform = PLATFORM_OPTIONS.find((p) => !used.has(p)) ?? "other";
    onChange({ ...value, [nextPlatform]: "" });
  }, [value, onChange, entries.length]);

  const handleRemove = useCallback(
    (key: string) => {
      const next = { ...value };
      delete next[key];
      onChange(next);
    },
    [value, onChange],
  );

  const handlePlatformChange = useCallback(
    (oldKey: string, newKey: string) => {
      if (oldKey === newKey) return;
      const next: Record<string, string> = {};
      for (const [k, v] of Object.entries(value)) {
        if (k === oldKey) {
          next[newKey] = v;
        } else {
          next[k] = v;
        }
      }
      onChange(next);
    },
    [value, onChange],
  );

  const handleUrlChange = useCallback(
    (key: string, url: string) => {
      onChange({ ...value, [key]: url });
    },
    [value, onChange],
  );

  return (
    <div className="space-y-3">
      <Label>Social Links</Label>

      {entries.length === 0 && (
        <p className="text-muted-foreground text-sm">No social links added yet.</p>
      )}

      {entries.map(([platform, url]) => (
        <div key={platform} className="flex items-center gap-2">
          <select
            value={platform}
            onChange={(e) => handlePlatformChange(platform, e.target.value)}
            disabled={disabled}
            className="h-9 w-32 shrink-0 rounded-md border border-input bg-transparent px-2 text-sm capitalize"
          >
            {PLATFORM_OPTIONS.map((opt) => (
              <option key={opt} value={opt}>
                {opt}
              </option>
            ))}
          </select>

          <Input
            value={url}
            onChange={(e) => handleUrlChange(platform, e.target.value)}
            placeholder="https://..."
            disabled={disabled}
            className="flex-1"
          />

          <Button
            type="button"
            variant="ghost"
            size="icon"
            onClick={() => handleRemove(platform)}
            disabled={disabled}
            className="shrink-0 text-muted-foreground hover:text-destructive"
          >
            <Trash2 className="h-4 w-4" />
            <span className="sr-only">Remove {platform}</span>
          </Button>
        </div>
      ))}

      {entries.length < MAX_LINKS && (
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={handleAdd}
          disabled={disabled}
        >
          <Plus className="mr-1.5 h-3.5 w-3.5" />
          Add Link
        </Button>
      )}
    </div>
  );
}
