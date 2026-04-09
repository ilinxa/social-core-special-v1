/**
 * Content Tree
 * ==============
 * Tree view of section placements → block placements for a page.
 * Click a block to select it for editing in BlockContentEditor.
 */

"use client";

import { ChevronDown, ChevronRight, FileText, LayoutTemplate } from "lucide-react";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { BLOCK_STATUS_CONFIG } from "@/features/cms/constants/cms-constants";
import type { CmsBlockPlacement, CmsSectionPlacement } from "@/features/cms/types";

type ContentTreeProps = {
  sections: CmsSectionPlacement[];
  selectedBlockId: string | null;
  onSelectBlock: (blockId: string) => void;
  publishErrors?: Map<string, { field_key: string; message: string }[]>;
};

export function ContentTree({
  sections,
  selectedBlockId,
  onSelectBlock,
  publishErrors,
}: ContentTreeProps) {
  return (
    <div role="tree" aria-label="Page content structure" className="space-y-1">
      {sections.map((section) => (
        <SectionNode
          key={section.id}
          section={section}
          selectedBlockId={selectedBlockId}
          onSelectBlock={onSelectBlock}
          publishErrors={publishErrors}
        />
      ))}
      {sections.length === 0 && (
        <p className="py-4 text-center text-sm text-muted-foreground">
          No sections on this page.
        </p>
      )}
    </div>
  );
}

function SectionNode({
  section,
  selectedBlockId,
  onSelectBlock,
  publishErrors,
}: {
  section: CmsSectionPlacement;
  selectedBlockId: string | null;
  onSelectBlock: (blockId: string) => void;
  publishErrors?: Map<string, { field_key: string; message: string }[]>;
}) {
  const [expanded, setExpanded] = useState(true);

  return (
    <div role="treeitem" aria-expanded={expanded} aria-selected={false}>
      <button
        type="button"
        className="flex w-full items-center gap-2 rounded px-2 py-1.5 text-sm hover:bg-muted/50"
        onClick={() => setExpanded(!expanded)}
      >
        {expanded ? (
          <ChevronDown className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
        ) : (
          <ChevronRight className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
        )}
        <LayoutTemplate className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
        <span className="truncate font-medium">
          {section.label || section.template.display_name}
        </span>
        {!section.is_visible && (
          <Badge variant="outline" className="ml-auto text-xs">
            Hidden
          </Badge>
        )}
      </button>
      {expanded && (
        <div className="ml-5 space-y-0.5 border-l pl-2">
          {section.block_placements.map((block) => (
            <BlockNode
              key={block.id}
              block={block}
              isSelected={selectedBlockId === block.id}
              onSelect={() => onSelectBlock(block.id)}
              hasErrors={publishErrors?.has(block.id) ?? false}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function BlockNode({
  block,
  isSelected,
  onSelect,
  hasErrors,
}: {
  block: CmsBlockPlacement;
  isSelected: boolean;
  onSelect: () => void;
  hasErrors: boolean;
}) {
  return (
    <button
      type="button"
      role="treeitem"
      aria-selected={isSelected}
      className={cn(
        "flex w-full items-center gap-2 rounded px-2 py-1.5 text-sm transition-colors",
        isSelected ? "bg-primary/10 text-primary" : "hover:bg-muted/50",
        hasErrors && "ring-1 ring-destructive",
      )}
      onClick={onSelect}
    >
      <FileText className="h-3.5 w-3.5 shrink-0" />
      <span className="truncate">
        {block.label || block.template.display_name}
      </span>
      <div className="ml-auto flex items-center gap-1">
        {!block.is_visible && (
          <Badge variant="outline" className="text-xs">
            Hidden
          </Badge>
        )}
        <div
          className={cn(
            "h-2 w-2 rounded-full",
            block.status === "published" ? "bg-green-500" : "bg-yellow-500",
          )}
          title={BLOCK_STATUS_CONFIG[block.status].label}
        />
      </div>
    </button>
  );
}
