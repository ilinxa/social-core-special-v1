/**
 * CMS Site Create Dialog
 * =======================
 * Form dialog for creating a new CMS site.
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
import { Textarea } from "@/components/ui/textarea";
import { ApiError } from "@/lib/api-client";
import { useCreateSite } from "@/features/cms/hooks/use-cms-mutations";
import type { CmsApiContext } from "@/features/cms/types";

type SiteCreateDialogProps = {
  context: CmsApiContext;
  open: boolean;
  onOpenChange: (open: boolean) => void;
};

function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
}

export function SiteCreateDialog({
  context,
  open,
  onOpenChange,
}: SiteCreateDialogProps) {
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [domain, setDomain] = useState("");
  const [description, setDescription] = useState("");
  const [slugError, setSlugError] = useState("");
  const createMutation = useCreateSite(context);

  function handleNameChange(value: string) {
    setName(value);
    if (!slug || slug === slugify(name)) {
      setSlug(slugify(value));
    }
  }

  function handleSubmit() {
    setSlugError("");
    createMutation.mutate(
      { name, slug, domain: domain || undefined, description: description || undefined },
      {
        onSuccess: () => {
          toast.success("Site created");
          onOpenChange(false);
          setName("");
          setSlug("");
          setDomain("");
          setDescription("");
        },
        onError: (error) => {
          if (error instanceof ApiError && error.isConflict) {
            setSlugError("This slug is already taken.");
          } else {
            toast.error("Failed to create site");
          }
        },
      },
    );
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create Site</DialogTitle>
          <DialogDescription>
            A site is a container for pages managed by the CMS.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-2">
          <div className="space-y-2">
            <Label htmlFor="site-name">Name</Label>
            <Input
              id="site-name"
              value={name}
              onChange={(e) => handleNameChange(e.target.value)}
              placeholder="My Website"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="site-slug">Slug</Label>
            <Input
              id="site-slug"
              value={slug}
              onChange={(e) => {
                setSlug(e.target.value);
                setSlugError("");
              }}
              placeholder="my-website"
            />
            {slugError && (
              <p className="text-sm text-destructive">{slugError}</p>
            )}
          </div>
          <div className="space-y-2">
            <Label htmlFor="site-domain">Domain (optional)</Label>
            <Input
              id="site-domain"
              value={domain}
              onChange={(e) => setDomain(e.target.value)}
              placeholder="example.com"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="site-description">Description (optional)</Label>
            <Textarea
              id="site-description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Internal description"
              rows={2}
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={!name || !slug || createMutation.isPending}
          >
            {createMutation.isPending ? "Creating..." : "Create Site"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
