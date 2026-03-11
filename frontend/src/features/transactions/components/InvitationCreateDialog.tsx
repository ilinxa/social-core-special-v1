"use client";

import { useState, useEffect, useRef, useMemo } from "react";
import { Search } from "lucide-react";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
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
import { RolePicker } from "@/components/common/RolePicker";
import { searchUsersApi } from "@/features/explore/api/explore-api";
import { fetchMembersApi } from "@/features/members/api/members-api";
import { fetchTransactionsApi } from "@/features/transactions/api/transactions-api";
import { useRoleList } from "@/features/members/hooks/use-role-queries";
import { useCreateInvitation } from "@/features/transactions/hooks/use-transaction-mutations";
import type { AccountType } from "@/types/rbac";
import type { ExploreUser } from "@/types/explore";

// =============================================================================
// TYPES
// =============================================================================

interface InvitationCreateDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  accountType: AccountType;
  accountId: string;
  slug: string;
  actorRoleLevel: number;
  maxMembers?: number;
}

type Step = "search" | "configure";

// =============================================================================
// COMPONENT
// =============================================================================

export function InvitationCreateDialog({
  open,
  onOpenChange,
  accountType,
  accountId,
  slug,
  actorRoleLevel,
  maxMembers = 0,
}: InvitationCreateDialogProps) {
  const [step, setStep] = useState<Step>("search");
  const [query, setQuery] = useState("");
  const [searchResults, setSearchResults] = useState<ExploreUser[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [selectedUser, setSelectedUser] = useState<ExploreUser | null>(null);
  const [selectedRoleId, setSelectedRoleId] = useState("");
  const [error, setError] = useState("");

  // Sets of user IDs that are already members or have pending transactions
  const [existingMemberIds, setExistingMemberIds] = useState<Set<string>>(new Set());
  const [pendingTransactionUsers, setPendingTransactionUsers] = useState<
    Map<string, "invitation" | "request">
  >(new Map());
  const [activeMemberCount, setActiveMemberCount] = useState(0);
  const [pendingCount, setPendingCount] = useState(0);

  const { data: roles } = useRoleList(accountType, slug);
  const createInvitation = useCreateInvitation();
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(null);

  // Auto-select Base Member role (or highest-level role) when roles load
  useEffect(() => {
    if (!roles || roles.length === 0 || selectedRoleId) return;
    const baseMember = roles.find(
      (r) => r.is_system_role && r.level === 10,
    );
    if (baseMember) {
      setSelectedRoleId(baseMember.id);
    } else {
      // Fallback: pick the role with the highest level number (lowest authority)
      const sorted = [...roles]
        .filter((r) => r.level > actorRoleLevel)
        .sort((a, b) => b.level - a.level);
      if (sorted[0]) {
        setSelectedRoleId(sorted[0].id);
      }
    }
  }, [roles, selectedRoleId, actorRoleLevel]);

  const transactionType =
    accountType === "business"
      ? "business_membership_invitation"
      : "platform_membership_invitation";

  // Compute quota status
  const totalCommitted = activeMemberCount + pendingCount;
  const isQuotaFull = maxMembers > 0 && totalCommitted >= maxMembers;

  // Fetch existing members and pending transaction counts when dialog opens
  useEffect(() => {
    if (!open || !accountId) return;

    fetchMembersApi(accountType, slug, { page_size: 200 })
      .then((res) => {
        const ids = new Set(res.results.map((m) => m.user.id));
        setExistingMemberIds(ids);
        setActiveMemberCount(res.count);
      })
      .catch(() => {});

    // Count pending membership invitations + requests AND extract user IDs
    Promise.all([
      fetchTransactionsApi({
        context_type: accountType,
        context_id: accountId,
        mode: "invitation",
        status: "pending",
      }),
      fetchTransactionsApi({
        context_type: accountType,
        context_id: accountId,
        mode: "request",
        status: "pending",
      }),
    ])
      .then(([invitations, requests]) => {
        setPendingCount(invitations.count + requests.count);

        // Build a map of user IDs with pending transactions
        const userMap = new Map<string, "invitation" | "request">();
        for (const txn of invitations.results) {
          if (txn.target_type === "user" && txn.target_id) {
            userMap.set(txn.target_id, "invitation");
          }
        }
        for (const txn of requests.results) {
          if (txn.initiator_type === "user" && txn.initiator_id) {
            userMap.set(txn.initiator_id, "request");
          }
        }
        setPendingTransactionUsers(userMap);
      })
      .catch(() => {});
  }, [open, accountId, accountType, slug]);

  // Debounced real-time search
  useEffect(() => {
    if (!open || step !== "search") return;

    const trimmed = query.trim();
    if (trimmed.length < 2) {
      setSearchResults([]);
      setHasSearched(false);
      return;
    }

    setIsSearching(true);

    if (debounceRef.current) clearTimeout(debounceRef.current);

    debounceRef.current = setTimeout(async () => {
      try {
        const result = await searchUsersApi({ q: trimmed, page_size: 10 });
        setSearchResults(result.results);
        setHasSearched(true);
      } catch {
        setSearchResults([]);
        setError("Failed to search users. Please try again.");
      } finally {
        setIsSearching(false);
      }
    }, 300);

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [query, open, step]);

  // Annotate search results: mark existing members and pending transactions
  const annotatedResults = useMemo(() => {
    return searchResults.map((user) => ({
      ...user,
      isMember: existingMemberIds.has(user.id),
      pendingTransactionType: pendingTransactionUsers.get(user.id) ?? null,
    }));
  }, [searchResults, existingMemberIds, pendingTransactionUsers]);

  function handleSelectUser(user: ExploreUser & { isMember?: boolean; pendingTransactionType?: string | null }) {
    if (user.isMember || user.pendingTransactionType) return;
    setSelectedUser(user);
    setStep("configure");
    setError("");
  }

  function handleBack() {
    setStep("search");
    setSelectedUser(null);
    setSelectedRoleId("");
    setError("");
  }

  function handleSubmit() {
    if (!selectedUser) return;

    setError("");
    createInvitation.mutate(
      {
        transaction_type: transactionType,
        target_user_id: selectedUser.id,
        context_type: accountType,
        context_id: accountId,
        payload: selectedRoleId ? { role_id: selectedRoleId } : undefined,
      },
      {
        onSuccess: () => {
          handleClose();
        },
        onError: (err: Error) => {
          const msg = err.message || "";

          if (msg.includes("maximum member limit")) {
            setError("Cannot send invitation — the member quota is full. Cancel pending invitations or increase the limit.");
          } else if (msg.includes("already an active member")) {
            setError("This user is already a member of this organization.");
          } else if (msg.includes("already exists") || msg.includes("active transaction")) {
            setError("An active invitation or request already exists for this user.");
          } else {
            setError(msg || "Failed to create invitation. Please try again.");
          }
        },
      },
    );
  }

  function handleClose() {
    setStep("search");
    setQuery("");
    setSearchResults([]);
    setHasSearched(false);
    setSelectedUser(null);
    setSelectedRoleId("");
    setError("");
    setExistingMemberIds(new Set());
    setPendingTransactionUsers(new Map());
    setActiveMemberCount(0);
    setPendingCount(0);
    onOpenChange(false);
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Invite Member</DialogTitle>
          <DialogDescription>
            {step === "search"
              ? "Search for a user to invite to your organization."
              : "Configure the invitation and send it."}
          </DialogDescription>
        </DialogHeader>

        {/* Quota warning */}
        {isQuotaFull && step === "search" && (
          <div className="rounded-md border border-destructive/50 bg-destructive/10 p-3">
            <p className="text-sm text-destructive">
              Member quota reached ({activeMemberCount} active + {pendingCount} pending
              = {totalCommitted}/{maxMembers}). Cancel pending invitations or increase the
              limit to invite more members.
            </p>
          </div>
        )}

        {/* Step 1: Search for a user */}
        {step === "search" && (
          <div className="space-y-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Search by name, username, or email..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="pl-9"
                autoFocus
                disabled={isQuotaFull}
              />
            </div>

            <div className="max-h-64 space-y-1 overflow-y-auto">
              {isSearching ? (
                Array.from({ length: 3 }, (_, i) => (
                  <div key={i} className="flex items-center gap-3 p-2">
                    <Skeleton className="h-8 w-8 rounded-full" />
                    <Skeleton className="h-4 w-32" />
                  </div>
                ))
              ) : annotatedResults.length === 0 && hasSearched ? (
                <p className="py-4 text-center text-sm text-muted-foreground">
                  No users found. Try a different search term.
                </p>
              ) : annotatedResults.length === 0 && !hasSearched ? (
                <p className="py-4 text-center text-sm text-muted-foreground">
                  Type at least 2 characters to search.
                </p>
              ) : (
                annotatedResults.map((user) => {
                  const isUnavailable = user.isMember || !!user.pendingTransactionType;
                  return (
                    <button
                      key={user.id}
                      className={`flex w-full items-center gap-3 rounded-md p-2 text-left transition-colors ${
                        isUnavailable
                          ? "cursor-not-allowed opacity-50"
                          : "hover:bg-muted"
                      }`}
                      onClick={() => handleSelectUser(user)}
                      disabled={isUnavailable}
                    >
                      <Avatar className="h-8 w-8">
                        {user.profile?.avatar_url && (
                          <AvatarImage src={user.profile.avatar_url} />
                        )}
                        <AvatarFallback className="text-xs">
                          {(user.display_name || user.username)
                            .charAt(0)
                            .toUpperCase()}
                        </AvatarFallback>
                      </Avatar>
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-medium">
                          {user.display_name || user.username}
                        </p>
                        <p className="truncate text-xs text-muted-foreground">
                          @{user.username} &middot; {user.email}
                        </p>
                      </div>
                      {user.isMember && (
                        <Badge variant="secondary" className="shrink-0 text-xs">
                          Member
                        </Badge>
                      )}
                      {!user.isMember && user.pendingTransactionType === "invitation" && (
                        <Badge variant="outline" className="shrink-0 text-xs">
                          Pending Invitation
                        </Badge>
                      )}
                      {!user.isMember && user.pendingTransactionType === "request" && (
                        <Badge variant="outline" className="shrink-0 text-xs">
                          Pending Request
                        </Badge>
                      )}
                    </button>
                  );
                })
              )}
            </div>
          </div>
        )}

        {/* Step 2: Configure invitation */}
        {step === "configure" && selectedUser && (
          <div className="space-y-4">
            {/* Selected user */}
            <div className="flex items-center gap-3 rounded-md border p-3">
              <Avatar className="h-10 w-10">
                {selectedUser.profile?.avatar_url && (
                  <AvatarImage src={selectedUser.profile.avatar_url} />
                )}
                <AvatarFallback>
                  {(selectedUser.display_name || selectedUser.username)
                    .charAt(0)
                    .toUpperCase()}
                </AvatarFallback>
              </Avatar>
              <div>
                <p className="font-medium">
                  {selectedUser.display_name || selectedUser.username}
                </p>
                <p className="text-sm text-muted-foreground">
                  @{selectedUser.username}
                </p>
              </div>
            </div>

            {/* Role selection */}
            <div className="space-y-2">
              <Label>Assign Role</Label>
              <p className="text-xs text-muted-foreground">
                The member will be assigned this role upon accepting the invitation.
              </p>
              {roles && (
                <RolePicker
                  roles={roles}
                  actorRoleLevel={actorRoleLevel}
                  value={selectedRoleId}
                  onChange={setSelectedRoleId}
                  label="Role"
                />
              )}
            </div>

            {/* Error */}
            {error && (
              <p className="text-sm text-destructive">{error}</p>
            )}
          </div>
        )}

        {/* Error for search step */}
        {step === "search" && error && (
          <p className="text-sm text-destructive">{error}</p>
        )}

        <DialogFooter>
          {step === "configure" ? (
            <>
              <Button
                variant="outline"
                onClick={handleBack}
                disabled={createInvitation.isPending}
              >
                Back
              </Button>
              <Button
                onClick={handleSubmit}
                disabled={createInvitation.isPending}
              >
                {createInvitation.isPending ? "Sending..." : "Send Invitation"}
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
