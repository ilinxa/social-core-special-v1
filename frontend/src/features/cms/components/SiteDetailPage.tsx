/**
 * CMS Site Detail Page
 * =====================
 * Site info + tabs (Pages, API Keys).
 * Tier 1.5: reads _permissions from GET detail for business context.
 */

"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Globe, Pencil, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Can } from "@/components/common/Can";
import { ConfirmActionDialog } from "@/components/common/ConfirmActionDialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useSite } from "@/features/cms/hooks/use-cms-queries";
import { useDeleteSite, useUpdateSite } from "@/features/cms/hooks/use-cms-mutations";
import { ApiKeyManagementPage } from "@/features/cms/components/ApiKeyManagementPage";
import { PageListPage } from "@/features/cms/components/PageListPage";
import type { CmsApiContext, CmsPermissions } from "@/features/cms/types";

type SiteDetailPageProps = {
  context: CmsApiContext;
  siteSlug: string;
  basePath: string;
};

export function SiteDetailPage({
  context,
  siteSlug,
  basePath,
}: SiteDetailPageProps) {
  const router = useRouter();
  const { data: site, isLoading } = useSite(context, siteSlug);
  const deleteMutation = useDeleteSite(context, siteSlug);
  const updateMutation = useUpdateSite(context, siteSlug);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [editing, setEditing] = useState(false);
  const [editName, setEditName] = useState("");
  const [editDomain, setEditDomain] = useState("");
  const [editDescription, setEditDescription] = useState("");

  const permissions = (
    site && "_permissions" in site ? site._permissions : null
  ) as CmsPermissions | null;

  if (isLoading) {
    return (
      <div className="space-y-6 p-6">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  if (!site) {
    return (
      <div className="p-6">
        <p className="text-muted-foreground">Site not found.</p>
      </div>
    );
  }

  function startEditing() {
    if (!site) return;
    setEditName(site.name);
    setEditDomain(site.domain);
    setEditDescription(site.description);
    setEditing(true);
  }

  function handleSave() {
    updateMutation.mutate(
      {
        name: editName || undefined,
        domain: editDomain || undefined,
        description: editDescription || undefined,
      },
      {
        onSuccess: () => {
          toast.success("Site updated");
          setEditing(false);
        },
        onError: () => toast.error("Failed to update site"),
      },
    );
  }

  function handleDelete() {
    deleteMutation.mutate(undefined, {
      onSuccess: () => {
        toast.success("Site deleted");
        router.push(`${basePath}/sites`);
      },
      onError: () => toast.error("Failed to delete site"),
    });
  }

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Globe className="h-6 w-6 text-muted-foreground" />
          <div>
            <h1 className="text-2xl font-bold">{site.name}</h1>
            <p className="text-sm text-muted-foreground">
              {site.slug}
              {site.domain ? ` \u00b7 ${site.domain}` : ""}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant={site.is_active ? "default" : "secondary"}>
            {site.is_active ? "Active" : "Inactive"}
          </Badge>
          <Can allowed={permissions?.can_edit_site}>
            <Button
              variant="outline"
              size="sm"
              onClick={startEditing}
            >
              <Pencil className="mr-1.5 h-4 w-4" />
              Edit
            </Button>
          </Can>
          <Can allowed={permissions?.can_delete_site}>
            <Button
              variant="destructive"
              size="sm"
              onClick={() => setDeleteOpen(true)}
            >
              <Trash2 className="mr-1.5 h-4 w-4" />
              Delete
            </Button>
          </Can>
        </div>
      </div>

      {/* Info card */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Site Details</CardTitle>
        </CardHeader>
        <CardContent>
          {editing ? (
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="edit-name">Name</Label>
                <Input
                  id="edit-name"
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit-domain">Domain</Label>
                <Input
                  id="edit-domain"
                  value={editDomain}
                  onChange={(e) => setEditDomain(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit-desc">Description</Label>
                <Textarea
                  id="edit-desc"
                  value={editDescription}
                  onChange={(e) => setEditDescription(e.target.value)}
                  rows={2}
                />
              </div>
              <div className="flex gap-2">
                <Button
                  size="sm"
                  onClick={handleSave}
                  disabled={updateMutation.isPending}
                >
                  {updateMutation.isPending ? "Saving..." : "Save"}
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setEditing(false)}
                >
                  Cancel
                </Button>
              </div>
            </div>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <p className="text-sm font-medium text-muted-foreground">
                  Locale
                </p>
                <p className="text-sm">{site.default_locale}</p>
              </div>
              <div>
                <p className="text-sm font-medium text-muted-foreground">
                  Description
                </p>
                <p className="text-sm">
                  {site.description || "No description"}
                </p>
              </div>
              <div>
                <p className="text-sm font-medium text-muted-foreground">
                  Created
                </p>
                <p className="text-sm">
                  {new Date(site.created_at).toLocaleDateString()}
                </p>
              </div>
              <div>
                <p className="text-sm font-medium text-muted-foreground">
                  Last Updated
                </p>
                <p className="text-sm">
                  {new Date(site.updated_at).toLocaleDateString()}
                </p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Tabs */}
      <Tabs defaultValue="pages">
        <TabsList>
          <TabsTrigger value="pages">Pages</TabsTrigger>
          <TabsTrigger value="api-keys">API Keys</TabsTrigger>
        </TabsList>
        <TabsContent value="pages">
          <PageListPage
            context={context}
            siteSlug={siteSlug}
            basePath={`${basePath}/sites/${siteSlug}`}
            permissions={permissions}
          />
        </TabsContent>
        <TabsContent value="api-keys">
          <ApiKeyManagementPage
            context={context}
            siteId={site.id}
            permissions={permissions}
          />
        </TabsContent>
      </Tabs>

      {/* Delete confirmation */}
      <ConfirmActionDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        title="Delete Site"
        description="This will permanently delete the site and all its pages. This action cannot be undone."
        confirmLabel="Delete Site"
        variant="destructive"
        onConfirm={handleDelete}
        isLoading={deleteMutation.isPending}
      />
    </div>
  );
}
