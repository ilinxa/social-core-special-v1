/**
 * API Key Management Page
 * ========================
 * List, create, and revoke CMS API keys for a site.
 * One-time key reveal dialog after creation.
 */

"use client";

import { useState } from "react";
import { Copy, Key, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
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
import { Skeleton } from "@/components/ui/skeleton";
import { Can } from "@/components/common/Can";
import { ConfirmActionDialog } from "@/components/common/ConfirmActionDialog";
import { useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/lib/query-keys";
import { useApiKeys } from "@/features/cms/hooks/use-cms-queries";
import {
  useCreateApiKey,
  useRevokeApiKey,
} from "@/features/cms/hooks/use-cms-mutations";
import { API_KEY_PREFIX } from "@/features/cms/constants/cms-constants";
import type { CmsApiContext, CmsApiKey, CmsPermissions } from "@/features/cms/types";

type ApiKeyManagementPageProps = {
  context: CmsApiContext;
  siteId: string;
  permissions?: CmsPermissions | null;
};

export function ApiKeyManagementPage({
  context,
  siteId,
  permissions,
}: ApiKeyManagementPageProps) {
  const queryClient = useQueryClient();
  const { data: keys, isLoading } = useApiKeys(context, siteId);
  const createMutation = useCreateApiKey(context);
  const revokeMutation = useRevokeApiKey(context);

  const [createOpen, setCreateOpen] = useState(false);
  const [revealedKey, setRevealedKey] = useState<string | null>(null);
  const [revokeTarget, setRevokeTarget] = useState<CmsApiKey | null>(null);

  // Create form state
  const [keyName, setKeyName] = useState("");
  const [rateLimit, setRateLimit] = useState("60");

  function handleCreate() {
    createMutation.mutate(
      { site_id: siteId, name: keyName, rate_limit: parseInt(rateLimit, 10) || 60 },
      {
        onSuccess: (data) => {
          setRevealedKey(data.key);
          setCreateOpen(false);
          setKeyName("");
          setRateLimit("60");
        },
        onError: () => toast.error("Failed to create API key"),
      },
    );
  }

  function handleRevealClose() {
    setRevealedKey(null);
    queryClient.invalidateQueries({ queryKey: queryKeys.cms.apiKeys(siteId) });
  }

  function handleRevoke() {
    if (!revokeTarget) return;
    revokeMutation.mutate(revokeTarget.id, {
      onSuccess: () => {
        toast.success("API key revoked");
        setRevokeTarget(null);
      },
      onError: () => toast.error("Failed to revoke key"),
    });
  }

  function copyToClipboard(text: string) {
    navigator.clipboard.writeText(text).then(
      () => toast.success("Copied to clipboard"),
      () => toast.error("Failed to copy"),
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">API Keys</h2>
        <Can allowed={permissions?.can_create_api_key ?? true}>
          <Button size="sm" onClick={() => setCreateOpen(true)}>
            <Plus className="mr-1.5 h-4 w-4" />
            Create Key
          </Button>
        </Can>
      </div>

      {/* Key list */}
      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 2 }, (_, i) => (
            <Skeleton key={i} className="h-16 w-full rounded-lg" />
          ))}
        </div>
      ) : !keys?.length ? (
        <p className="py-8 text-center text-muted-foreground">
          No API keys yet.
        </p>
      ) : (
        <ul className="space-y-2">
          {keys.map((key: CmsApiKey) => (
            <li
              key={key.id}
              className="flex items-center justify-between rounded-lg border p-4"
            >
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <Key className="h-4 w-4 text-muted-foreground" />
                  <span className="font-medium">{key.name}</span>
                  <Badge variant={key.is_active ? "default" : "secondary"}>
                    {key.is_active ? "Active" : "Revoked"}
                  </Badge>
                </div>
                <p className="text-sm text-muted-foreground">
                  {key.key_prefix}... &middot; {key.rate_limit} req/min
                  {key.last_used_at &&
                    ` \u00b7 Last used ${new Date(key.last_used_at).toLocaleDateString()}`}
                </p>
              </div>
              {key.is_active && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-destructive hover:text-destructive"
                  onClick={() => setRevokeTarget(key)}
                >
                  <Trash2 className="mr-1 h-3.5 w-3.5" />
                  Revoke
                </Button>
              )}
            </li>
          ))}
        </ul>
      )}

      {/* Create dialog */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create API Key</DialogTitle>
            <DialogDescription>
              Create a key for external CMS access. The full key is shown only once.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label htmlFor="key-name">Name</Label>
              <Input
                id="key-name"
                value={keyName}
                onChange={(e) => setKeyName(e.target.value)}
                placeholder="Production Website"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="key-rate">Rate Limit (req/min)</Label>
              <Input
                id="key-rate"
                type="number"
                min={1}
                value={rateLimit}
                onChange={(e) => setRateLimit(e.target.value)}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleCreate}
              disabled={!keyName || createMutation.isPending}
            >
              {createMutation.isPending ? "Creating..." : "Create Key"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Key reveal dialog (one-time) */}
      <Dialog open={revealedKey !== null} onOpenChange={() => handleRevealClose()}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>API Key Created</DialogTitle>
            <DialogDescription>
              Copy this key now. It will not be shown again.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3 py-2">
            <div className="flex items-center gap-2 rounded-lg bg-muted p-3">
              <code className="flex-1 break-all text-sm">{revealedKey}</code>
              <Button
                variant="ghost"
                size="icon"
                aria-label="Copy"
                onClick={() => revealedKey && copyToClipboard(revealedKey)}
              >
                <Copy className="h-4 w-4" />
              </Button>
            </div>
            <p className="text-sm text-destructive">
              This key starts with &quot;{API_KEY_PREFIX}&quot; and cannot be retrieved after closing this dialog.
            </p>
          </div>
          <DialogFooter>
            <Button onClick={handleRevealClose}>Done</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Revoke confirmation */}
      <ConfirmActionDialog
        open={revokeTarget !== null}
        onOpenChange={(v) => !v && setRevokeTarget(null)}
        title="Revoke API Key"
        description={`Revoke "${revokeTarget?.name}"? This action cannot be undone. External applications using this key will lose access immediately.`}
        confirmLabel="Revoke Key"
        variant="destructive"
        onConfirm={handleRevoke}
        isLoading={revokeMutation.isPending}
      />
    </div>
  );
}
