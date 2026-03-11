"use client";

import { useMemo, useRef, useState } from "react";
import { X } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { useTagSuggestions } from "@/features/explore/hooks/use-explore-queries";

interface TagInputProps {
  value: string;
  onChange: (value: string) => void;
  category: "user" | "business";
}

export function TagInput({ value, onChange, category }: TagInputProps) {
  const [inputValue, setInputValue] = useState("");
  const [showSuggestions, setShowSuggestions] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const tags = useMemo(
    () => (value ? value.split(",").filter(Boolean) : []),
    [value],
  );

  const { data: suggestions } = useTagSuggestions(
    inputValue.length >= 1 ? inputValue : undefined,
    category,
  );

  const filteredSuggestions = useMemo(
    () =>
      (suggestions ?? []).filter(
        (s) => !tags.includes(s.name),
      ),
    [suggestions, tags],
  );

  function addTag(tag: string) {
    const trimmed = tag.trim().toLowerCase();
    if (!trimmed || tags.includes(trimmed)) return;
    const next = [...tags, trimmed].join(",");
    onChange(next);
    setInputValue("");
    setShowSuggestions(false);
    inputRef.current?.focus();
  }

  function removeTag(tag: string) {
    const next = tags.filter((t) => t !== tag).join(",");
    onChange(next);
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
    <div className="relative">
      <div className="flex min-h-8 flex-wrap items-center gap-1 rounded-md border bg-background px-2 py-1 text-xs focus-within:ring-1 focus-within:ring-ring">
        {tags.map((tag) => (
          <Badge key={tag} variant="secondary" className="h-5 gap-0.5 px-1.5 text-[10px]">
            {tag}
            <button
              type="button"
              onClick={() => removeTag(tag)}
              className="ml-0.5 rounded-sm hover:bg-muted-foreground/20"
            >
              <X className="h-2.5 w-2.5" />
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
            // Delay to allow click on suggestion
            setTimeout(() => setShowSuggestions(false), 150);
          }}
          onKeyDown={handleKeyDown}
          placeholder={tags.length === 0 ? "Add tags..." : ""}
          className="h-5 min-w-16 flex-1 border-0 px-0 text-xs shadow-none focus-visible:ring-0"
        />
      </div>

      {/* Suggestions dropdown */}
      {showSuggestions && filteredSuggestions.length > 0 && (
        <div className="absolute z-50 mt-1 w-full rounded-md border bg-popover p-1 shadow-md">
          {filteredSuggestions.slice(0, 8).map((suggestion) => (
            <button
              key={suggestion.id}
              type="button"
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => addTag(suggestion.name)}
              className="flex w-full items-center rounded-sm px-2 py-1 text-xs hover:bg-accent"
            >
              {suggestion.name}
              <span className="ml-auto text-[10px] text-muted-foreground">
                {suggestion.usage_count}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
