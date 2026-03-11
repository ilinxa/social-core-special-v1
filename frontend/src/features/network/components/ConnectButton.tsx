"use client";

import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { ConfirmActionDialog } from "@/components/common/ConfirmActionDialog";
import { useIsAuthenticated } from "@/stores/auth-store";
import { useConnectUser, useDisconnectUser } from "@/features/network/hooks/use-network-mutations";
import {
  useCancelTransaction,
  useAcceptTransaction,
  useDenyTransaction,
} from "@/features/transactions/hooks/use-transaction-mutations";
import type { ActiveTransactionSummary } from "@/types/organization";

interface ConnectButtonProps {
  targetUserId: string;
  targetUsername: string;
  connectionStatus: string | null;
  connectionId: string | null;
  activeConnectionTransaction: ActiveTransactionSummary | null;
  onAction?: () => void;
  size?: "default" | "sm";
}

export function ConnectButton({
  targetUserId,
  targetUsername,
  connectionStatus,
  connectionId,
  activeConnectionTransaction,
  onAction,
  size = "default",
}: ConnectButtonProps) {
  const isAuthenticated = useIsAuthenticated();
  const connectUser = useConnectUser();
  const disconnectUser = useDisconnectUser();
  const cancelTransaction = useCancelTransaction();
  const acceptTransaction = useAcceptTransaction();
  const denyTransaction = useDenyTransaction();

  const [isHovered, setIsHovered] = useState(false);
  const [connectDialogOpen, setConnectDialogOpen] = useState(false);
  const [disconnectDialogOpen, setDisconnectDialogOpen] = useState(false);
  const [declineDialogOpen, setDeclineDialogOpen] = useState(false);

  if (!isAuthenticated) return null;

  const isConnected = connectionStatus === "active";
  const isPendingInitiator =
    !isConnected &&
    activeConnectionTransaction?.viewer_role === "initiator";
  const isPendingTarget =
    !isConnected &&
    activeConnectionTransaction?.viewer_role === "target";

  function handleConnect(note?: string) {
    connectUser.mutate(
      { target_user_id: targetUserId, note: note || undefined },
      {
        onSuccess: () => {
          setConnectDialogOpen(false);
          toast.success("Connection request sent");
          onAction?.();
        },
        onError: (error) => {
          toast.error("Request failed", {
            description:
              error instanceof Error ? error.message : "Could not send request.",
          });
        },
      },
    );
  }

  function handleCancelRequest() {
    if (!activeConnectionTransaction) return;
    cancelTransaction.mutate(
      { transactionId: activeConnectionTransaction.id },
      {
        onSuccess: () => {
          toast.success("Request cancelled");
          onAction?.();
        },
        onError: (error) => {
          toast.error("Cancel failed", {
            description:
              error instanceof Error ? error.message : "Could not cancel.",
          });
        },
      },
    );
  }

  function handleAccept() {
    if (!activeConnectionTransaction) return;
    acceptTransaction.mutate(
      { transactionId: activeConnectionTransaction.id },
      {
        onSuccess: () => {
          toast.success("Connection accepted");
          onAction?.();
        },
        onError: (error) => {
          toast.error("Accept failed", {
            description:
              error instanceof Error ? error.message : "Could not accept.",
          });
        },
      },
    );
  }

  function handleDecline() {
    if (!activeConnectionTransaction) return;
    denyTransaction.mutate(
      { transactionId: activeConnectionTransaction.id },
      {
        onSuccess: () => {
          setDeclineDialogOpen(false);
          toast.success("Request declined");
          onAction?.();
        },
        onError: (error) => {
          toast.error("Decline failed", {
            description:
              error instanceof Error ? error.message : "Could not decline.",
          });
        },
      },
    );
  }

  function handleDisconnect() {
    if (!connectionId) return;
    disconnectUser.mutate(connectionId, {
      onSuccess: () => {
        setDisconnectDialogOpen(false);
        toast.success("Disconnected");
        onAction?.();
      },
      onError: (error) => {
        toast.error("Disconnect failed", {
          description:
            error instanceof Error ? error.message : "Could not disconnect.",
        });
      },
    });
  }

  // State: Pending request sent by viewer — show Cancel
  if (isPendingInitiator) {
    return (
      <Button
        variant="outline"
        size={size}
        onClick={handleCancelRequest}
        disabled={cancelTransaction.isPending}
      >
        {cancelTransaction.isPending ? "Cancelling..." : "Cancel Request"}
      </Button>
    );
  }

  // State: Incoming connection request — show Accept/Decline
  if (isPendingTarget) {
    return (
      <div className="flex gap-2">
        <Button
          size={size}
          onClick={handleAccept}
          disabled={acceptTransaction.isPending}
        >
          {acceptTransaction.isPending ? "Accepting..." : "Accept"}
        </Button>
        <Button
          variant="ghost"
          size={size}
          onClick={() => setDeclineDialogOpen(true)}
          disabled={denyTransaction.isPending}
        >
          Decline
        </Button>

        <ConfirmActionDialog
          open={declineDialogOpen}
          onOpenChange={setDeclineDialogOpen}
          title="Decline connection?"
          description={`Decline the connection request from @${targetUsername}?`}
          confirmLabel="Decline"
          variant="destructive"
          onConfirm={handleDecline}
          isLoading={denyTransaction.isPending}
        />
      </div>
    );
  }

  // State: Already connected — hover to show Disconnect
  if (isConnected) {
    return (
      <>
        <Button
          variant={isHovered ? "destructive" : "secondary"}
          size={size}
          onMouseEnter={() => setIsHovered(true)}
          onMouseLeave={() => setIsHovered(false)}
          onClick={() => setDisconnectDialogOpen(true)}
        >
          {isHovered ? "Disconnect" : "Connected"}
        </Button>

        <ConfirmActionDialog
          open={disconnectDialogOpen}
          onOpenChange={setDisconnectDialogOpen}
          title="Disconnect?"
          description={`Remove your connection with @${targetUsername}?`}
          confirmLabel="Disconnect"
          variant="destructive"
          onConfirm={handleDisconnect}
          isLoading={disconnectUser.isPending}
        />
      </>
    );
  }

  // State: Not connected — show Connect button with note dialog
  return (
    <>
      <Button
        variant="outline"
        size={size}
        onClick={() => setConnectDialogOpen(true)}
        disabled={connectUser.isPending}
      >
        Connect
      </Button>

      <ConfirmActionDialog
        open={connectDialogOpen}
        onOpenChange={setConnectDialogOpen}
        title="Send Connection Request"
        description={`Send a connection request to @${targetUsername}`}
        confirmLabel="Send Request"
        showReasonField
        reasonRequired={false}
        reasonLabel="Note (optional)"
        onConfirm={handleConnect}
        isLoading={connectUser.isPending}
      />
    </>
  );
}
