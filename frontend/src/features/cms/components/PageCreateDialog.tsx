/**
 * CMS Page Create Dialog
 * =======================
 * Form dialog for creating a new CMS page within a site.
 */

"use client";

import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ApiError } from "@/lib/api-client";
import { useCreatePage } from "@/features/cms/hooks/use-cms-mutations";
import { useSite } from "@/features/cms/hooks/use-cms-queries";
import type { CmsApiContext } from "@/features/cms/types";

const PAGE_TYPES = ["landing", "content", "legal", "blog_post"] as const;

type PageCreateDialogProps = {
  context: CmsApiContext;
  siteSlug: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
};

function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
}

export function PageCreateDialog({
  context,
  siteSlug,
  open,
  onOpenChange,
}: PageCreateDialogProps) {
  const { data: site } = useSite(context, siteSlug);
  const createMutation = useCreatePage(context);

  const [title, setTitle] = useState("");
  const [slug, setSlug] = useState("");
  const [path, setPath] = useState("");
  const [pageType, setPageType] = useState<string>("content");
  const [order, setOrder] = useState("0");
  const [slugError, setSlugError] = useState("");

  function handleTitleChange(value: string) {
    setTitle(value);
    const newSlug = slugify(value);
    if (!slug || slug === slugify(title)) {
      setSlug(newSlug);
      setPath(`/${newSlug}`);
    }
  }

  function handleSubmit() {
    if (!site) return;
    setSlugError("");

    createMutation.mutate(
      {
        site_id: site.id,
        title,
        slug,
        path: path || `/${slug}`,
        page_type: pageType,
        order: parseInt(order, 10) || 0,
      },
      {
        onSuccess: () => {
          toast.success("Page created");
          onOpenChange(false);
          setTitle("");
          setSlug("");
          setPath("");
          setOrder("0");
        },
        onError: (error) => {
          if (error instanceof ApiError && error.isConflict) {
            setSlugError("This slug already exists in this site.");
          } else {
            toast.error("Failed to create page");
          }
        },
      },
    );
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create Page</DialogTitle>
          <DialogDescription>
            Add a new page to {site?.name ?? "this site"}.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-2">
          <div className="space-y-2">
            <Label htmlFor="page-title">Title</Label>
            <Input
              id="page-title"
              value={title}
              onChange={(e) => handleTitleChange(e.target.value)}
              placeholder="Home"
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="page-slug">Slug</Label>
              <Input
                id="page-slug"
                value={slug}
                onChange={(e) => {
                  setSlug(e.target.value);
                  setSlugError("");
                }}
                placeholder="home"
              />
              {slugError && (
                <p className="text-sm text-destructive">{slugError}</p>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="page-path">Path</Label>
              <Input
                id="page-path"
                value={path}
                onChange={(e) => setPath(e.target.value)}
                placeholder="/home"
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Page Type</Label>
              <Select value={pageType} onValueChange={setPageType}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {PAGE_TYPES.map((t) => (
                    <SelectItem key={t} value={t}>
                      {t.replace("_", " ").replace(/\b\w/g, (c) => c.toUpperCase())}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="page-order">Order</Label>
              <Input
                id="page-order"
                type="number"
                min={0}
                value={order}
                onChange={(e) => setOrder(e.target.value)}
              />
            </div>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={!title || !slug || createMutation.isPending}
          >
            {createMutation.isPending ? "Creating..." : "Create Page"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
