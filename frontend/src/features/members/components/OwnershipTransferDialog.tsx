"use client";

import { useState, useMemo } from "react";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
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
import { useMemberList } from "@/features/members/hooks/use-member-queries";
import { useCreateInvitation } from "@/features/transactions/hooks/use-transaction-mutations";
import type { AccountType } from "@/types/rbac";
import type { MemberListItem } from "@/types/members";

const CONFIRMATION_PHRASE = "transfer ownership";

interface OwnershipTransferDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  accountType: AccountType;
  slug: string;
  accountId: string;
}

export function OwnershipTransferDialog({
  open,
  onOpenChange,
  accountType,
  slug,
  accountId,
}: OwnershipTransferDialogProps) {
  const [step, setStep] = useState<"select" | "confirm">("select");
  const [selectedMember, setSelectedMember] = useState<MemberListItem | null>(
    null,
  );
  const [confirmText, setConfirmText] = useState("");

  const { data, isLoading } = useMemberList(accountType, slug, {
    status: "active",
    page_size: 100,
  });

  const createInvitation = useCreateInvitation();

  // Filter out the current owner — only show active non-owner members
  const eligibleMembers = useMemo(
    () => data?.results.filter((m) => !m.is_owner) ?? [],
    [data],
  );

  const isConfirmed =
    confirmText.toLowerCase().trim() === CONFIRMATION_PHRASE;

  function handleSelectMember(member: MemberListItem) {
    setSelectedMember(member);
    setStep("confirm");
  }

  function handleBack() {
    setStep("select");
    setConfirmText("");
  }

  function handleTransfer() {
    if (!selectedMember || !isConfirmed) return;

    const transactionType =
      accountType === "business"
        ? "business_ownership_transfer"
        : "platform_ownership_transfer";

    createInvitation.mutate(
      {
        transaction_type: transactionType,
        target_user_id: selectedMember.user.id,
        context_type: accountType,
        context_id: accountId,
      },
      {
        onSuccess: () => {
          handleClose();
        },
      },
    );
  }

  function handleClose() {
    setStep("select");
    setSelectedMember(null);
    setConfirmText("");
    onOpenChange(false);
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Transfer Ownership</DialogTitle>
          <DialogDescription>
            {step === "select"
              ? "Select a member to transfer ownership to. They must accept the transfer."
              : "This action is irreversible. You will lose all owner privileges."}
          </DialogDescription>
        </DialogHeader>

        {step === "select" && (
          <div className="max-h-64 space-y-1 overflow-y-auto">
            {isLoading ? (
              Array.from({ length: 3 }, (_, i) => (
                <div key={i} className="flex items-center gap-3 p-2">
                  <Skeleton className="h-8 w-8 rounded-full" />
                  <Skeleton className="h-4 w-32" />
                </div>
              ))
            ) : eligibleMembers.length === 0 ? (
              <p className="py-4 text-center text-sm text-muted-foreground">
                No eligible members. You need at least one other active member
                to transfer ownership.
              </p>
            ) : (
              eligibleMembers.map((member) => (
                <button
                  key={member.id}
                  className="flex w-full items-center gap-3 rounded-md p-2 text-left transition-colors hover:bg-muted"
                  onClick={() => handleSelectMember(member)}
                >
                  <Avatar className="h-8 w-8">
                    {member.user.avatar_url && (
                      <AvatarImage src={member.user.avatar_url} />
                    )}
                    <AvatarFallback className="text-xs">
                      {(member.user.display_name || member.user.username)
                        .charAt(0)
                        .toUpperCase()}
                    </AvatarFallback>
                  </Avatar>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">
                      {member.user.display_name || member.user.username}
                    </p>
                    <p className="truncate text-xs text-muted-foreground">
                      {member.user.email} &middot; {member.role_name}
                    </p>
                  </div>
                </button>
              ))
            )}
          </div>
        )}

        {step === "confirm" && selectedMember && (
          <div className="space-y-4">
            {/* Selected member */}
            <div className="flex items-center gap-3 rounded-md border p-3">
              <Avatar className="h-10 w-10">
                {selectedMember.user.avatar_url && (
                  <AvatarImage src={selectedMember.user.avatar_url} />
                )}
                <AvatarFallback>
                  {(
                    selectedMember.user.display_name ||
                    selectedMember.user.username
                  )
                    .charAt(0)
                    .toUpperCase()}
                </AvatarFallback>
              </Avatar>
              <div>
                <p className="font-medium">
                  {selectedMember.user.display_name ||
                    selectedMember.user.username}
                </p>
                <p className="text-sm text-muted-foreground">
                  {selectedMember.user.email}
                </p>
              </div>
            </div>

            {/* Warning */}
            <div className="rounded-md border border-destructive/50 bg-destructive/5 p-3 text-sm">
              <p className="font-medium text-destructive">Warning</p>
              <ul className="mt-1 list-inside list-disc space-y-1 text-muted-foreground">
                <li>You will be demoted to Base Member</li>
                <li>The selected member will become the new owner</li>
                <li>This cannot be undone unless the new owner transfers back</li>
                <li>The transfer must be accepted by the target member</li>
              </ul>
            </div>

            {/* Confirmation input */}
            <div className="space-y-2">
              <Label htmlFor="confirm-transfer">
                Type <strong>{CONFIRMATION_PHRASE}</strong> to confirm
              </Label>
              <Input
                id="confirm-transfer"
                value={confirmText}
                onChange={(e) => setConfirmText(e.target.value)}
                placeholder={CONFIRMATION_PHRASE}
                disabled={createInvitation.isPending}
              />
            </div>
          </div>
        )}

        <DialogFooter>
          {step === "confirm" ? (
            <>
              <Button
                variant="outline"
                onClick={handleBack}
                disabled={createInvitation.isPending}
              >
                Back
              </Button>
              <Button
                variant="destructive"
                onClick={handleTransfer}
                disabled={!isConfirmed || createInvitation.isPending}
              >
                {createInvitation.isPending
                  ? "Transferring..."
                  : "Transfer Ownership"}
              </Button>
            </>
          ) : (
            <Button variant="outline" onClick={handleClose}>
              Cancel
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
