"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { Search } from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Can } from "@/components/common/Can";
import { ConfirmActionDialog } from "@/components/common/ConfirmActionDialog";
import { useHasPermission } from "@/hooks/use-has-permission";
import { useBusinessMemberships } from "@/stores/membership-store";
import {
  useBusinessConnections,
  useBusinessNetworkStats,
} from "@/features/network/hooks/use-network-queries";
import { useBusinessDisconnect } from "@/features/network/hooks/use-network-mutations";
import type { AccountConnectionItem } from "@/types/network";

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function AccountConnectionCard({
  connection,
  canManage,
  onDisconnect,
  isDisconnecting,
}: {
  connection: AccountConnectionItem;
  canManage: boolean;
  onDisconnect: (connectionId: string) => void;
  isDisconnecting: boolean;
}) {
  const [dialogOpen, setDialogOpen] = useState(false);

  return (
    <div className="flex items-center gap-4 rounded-lg border p-4">
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <p className="text-sm font-medium">{connection.other_account.name}</p>
          <Badge variant="secondary" className="text-xs capitalize">
            {connection.other_account.type}
          </Badge>
        </div>
        {connection.note && (
          <p className="text-muted-foreground mt-1 truncate text-xs italic">
            &ldquo;{connection.note}&rdquo;
          </p>
        )}
      </div>

      <div className="flex shrink-0 items-center gap-3">
        {connection.connected_at && (
          <span className="text-muted-foreground hidden text-xs sm:block">
            {formatDate(connection.connected_at)}
          </span>
        )}
        <Can allowed={canManage}>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setDialogOpen(true)}
            disabled={isDisconnecting}
          >
            Disconnect
          </Button>
        </Can>
      </div>

      <ConfirmActionDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        title="Disconnect?"
        description={`Remove connection with ${connection.other_account.name}?`}
        confirmLabel="Disconnect"
        variant="destructive"
        onConfirm={() => onDisconnect(connection.id)}
        isLoading={isDisconnecting}
      />
    </div>
  );
}

export function BusinessConnectionsPage() {
  const { slug } = useParams<{ slug: string }>();
  const [search, setSearch] = useState("");
  const memberships = useBusinessMemberships();
  const myMembership = memberships.find((m) => m.account_slug === slug);
  const accountId = myMembership?.account_id ?? "";
  const canManage = useHasPermission("can_manage_connections", "business", accountId);
  const { data, isLoading } = useBusinessConnections(slug);
  const { data: stats } = useBusinessNetworkStats(slug);
  const disconnectBusiness = useBusinessDisconnect(slug);

  function handleDisconnect(connectionId: string) {
    disconnectBusiness.mutate(connectionId, {
      onSuccess: () => toast.success("Disconnected"),
      onError: (error) =>
        toast.error("Failed", {
          description:
            error instanceof Error ? error.message : "Could not disconnect.",
        }),
    });
  }

  const connections = data?.results ?? [];
  const filtered = search
    ? connections.filter((c) =>
        c.other_account.name.toLowerCase().includes(search.toLowerCase()),
      )
    : connections;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold tracking-tight">Connections</h1>
        {stats && (
          <span className="text-muted-foreground text-sm">
            {stats.connections_count} connections
          </span>
        )}
      </div>

      <div className="relative">
        <Search className="text-muted-foreground absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2" />
        <Input
          placeholder="Search connections..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-10"
        />
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="flex items-center gap-4 rounded-lg border p-4">
              <div className="flex-1 space-y-2">
                <Skeleton className="h-4 w-40" />
                <Skeleton className="h-3 w-24" />
              </div>
              <Skeleton className="h-8 w-24" />
            </div>
          ))}
        </div>
      ) : filtered.length > 0 ? (
        <div className="space-y-3">
          {filtered.map((connection) => (
            <AccountConnectionCard
              key={connection.id}
              connection={connection}
              canManage={canManage}
              onDisconnect={handleDisconnect}
              isDisconnecting={disconnectBusiness.isPending}
            />
          ))}
        </div>
      ) : (
        <p className="text-muted-foreground py-12 text-center text-sm">
          {search
            ? "No connections match your search."
            : "No connections yet."}
        </p>
      )}
    </div>
  );
}
