"use client";

import { useMemo, useRef, useState } from "react";
import { X } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useTagSuggestions } from "@/hooks/use-tag-suggestions";

interface FormTagInputProps {
  label: string;
  value: string[];
  onChange: (value: string[]) => void;
  category: "user" | "business";
  error?: string;
  maxTags?: number;
}

export function FormTagInput({
  label,
  value,
  onChange,
  category,
  error,
  maxTags = 20,
}: FormTagInputProps) {
  const [inputValue, setInputValue] = useState("");
  const [showSuggestions, setShowSuggestions] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const { data: suggestions } = useTagSuggestions(
    inputValue.length >= 1 ? inputValue : undefined,
    category,
  );

  const tags = value ?? [];

  const filteredSuggestions = useMemo(
    () => (suggestions ?? []).filter((s) => !tags.includes(s.name)),
    [suggestions, tags],
  );

  function addTag(tag: string) {
    const trimmed = tag.trim().toLowerCase();
    if (!trimmed || tags.includes(trimmed) || tags.length >= maxTags) return;
    onChange([...tags, trimmed]);
    setInputValue("");
    setShowSuggestions(false);
    inputRef.current?.focus();
  }

  function removeTag(tag: string) {
    onChange(tags.filter((t) => t !== tag));
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if ((e.key === "Enter" || e.key === ",") && inputValue.trim()) {
      e.preventDefault();
      addTag(inputValue);
    }
    if (e.key === "Backspace" && !inputValue && tags.length > 0) {
      removeTag(tags[tags.length - 1]);
    }
  }

  return (
    <div className="space-y-2">
      <Label>{label}</Label>
      <div className="relative">
        <div className="flex min-h-10 flex-wrap items-center gap-1.5 rounded-md border bg-background px-3 py-2 text-sm focus-within:ring-1 focus-within:ring-ring">
          {tags.map((tag) => (
            <Badge key={tag} variant="secondary" className="gap-1 px-2 py-0.5 text-xs">
              {tag}
              <button
                type="button"
                onClick={() => removeTag(tag)}
                aria-label={`Remove ${tag}`}
                className="ml-0.5 rounded-sm hover:bg-muted-foreground/20"
              >
                <X className="h-3 w-3" />
              </button>
            </Badge>
          ))}
          <Input
            ref={inputRef}
            value={inputValue}
            onChange={(e) => {
              setInputValue(e.target.value);
              setShowSuggestions(true);
            }}
            onFocus={() => setShowSuggestions(true)}
            onBlur={() => {
              setTimeout(() => setShowSuggestions(false), 150);
            }}
            onKeyDown={handleKeyDown}
            placeholder={tags.length === 0 ? "Add tags..." : ""}
            className="h-6 min-w-20 flex-1 border-0 px-0 text-sm shadow-none focus-visible:ring-0"
          />
        </div>

        {showSuggestions && filteredSuggestions.length > 0 && (
          <div className="absolute z-50 mt-1 w-full rounded-md border bg-popover p-1 shadow-md">
            {filteredSuggestions.slice(0, 8).map((suggestion) => (
              <button
                key={suggestion.id}
                type="button"
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => addTag(suggestion.name)}
                className="flex w-full items-center rounded-sm px-2 py-1.5 text-sm hover:bg-accent"
              >
                {suggestion.name}
                <span className="ml-auto text-xs text-muted-foreground">
                  {suggestion.usage_count}
                </span>
              </button>
            ))}
          </div>
        )}
      </div>
      {error && <p className="text-destructive text-sm">{error}</p>}
    </div>
  );
}
