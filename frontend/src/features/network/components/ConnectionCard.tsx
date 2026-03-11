"use client";

import { useState } from "react";
import Link from "next/link";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { ConfirmActionDialog } from "@/components/common/ConfirmActionDialog";
import type { UserConnectionItem } from "@/types/network";

interface ConnectionCardProps {
  connection: UserConnectionItem;
  onDisconnect: (connectionId: string) => void;
  isDisconnecting?: boolean;
}

function getInitials(name: string): string {
  return name[0]?.toUpperCase() ?? "?";
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export function ConnectionCard({
  connection,
  onDisconnect,
  isDisconnecting = false,
}: ConnectionCardProps) {
  const [dialogOpen, setDialogOpen] = useState(false);
  const { other_user, note, connected_at } = connection;

  return (
    <div className="flex items-center gap-4 rounded-lg border p-4">
      <Link href={`/users/${other_user.username}`}>
        <Avatar className="h-10 w-10">
          <AvatarImage src={other_user.avatar_url} alt={other_user.display_name} />
          <AvatarFallback>{getInitials(other_user.display_name)}</AvatarFallback>
        </Avatar>
      </Link>

      <div className="min-w-0 flex-1">
        <Link
          href={`/users/${other_user.username}`}
          className="text-sm font-medium hover:underline"
        >
          {other_user.display_name}
        </Link>
        <p className="text-muted-foreground text-xs">@{other_user.username}</p>
        {note && (
          <p className="text-muted-foreground mt-1 truncate text-xs italic">
            &ldquo;{note}&rdquo;
          </p>
        )}
      </div>

      <div className="flex shrink-0 items-center gap-3">
        {connected_at && (
          <span className="text-muted-foreground hidden text-xs sm:block">
            {formatDate(connected_at)}
          </span>
        )}
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setDialogOpen(true)}
          disabled={isDisconnecting}
        >
          Disconnect
        </Button>
      </div>

      <ConfirmActionDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        title="Disconnect?"
        description={`Remove your connection with ${other_user.display_name}?`}
        confirmLabel="Disconnect"
        variant="destructive"
        onConfirm={() => onDisconnect(connection.id)}
        isLoading={isDisconnecting}
      />
    </div>
  );
}
