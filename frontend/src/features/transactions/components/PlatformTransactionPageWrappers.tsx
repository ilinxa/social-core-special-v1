"use client";

import { useParams } from "next/navigation";

import { usePlatformMembership } from "@/stores/membership-store";
import { RequestsListPage } from "./RequestsListPage";
import { InvitationsListPage } from "./InvitationsListPage";
import { TransactionDetailPage } from "./TransactionDetailPage";
import { TransactionSettingsPage } from "./TransactionSettingsPage";

function usePlatformContext() {
  const myMembership = usePlatformMembership();
  const accountId = myMembership?.account_id ?? "";
  const actorRoleLevel = myMembership?.role?.level ?? 999;
  const maxMembers = myMembership?.account_max_members ?? 0;
  const basePath = "/pconsole/transactions";
  return { accountId, actorRoleLevel, maxMembers, basePath };
}

export function PlatformRequestsListPage() {
  const { accountId, basePath } = usePlatformContext();
  return (
    <RequestsListPage
      accountType="platform"
      accountId={accountId}
      basePath={basePath}
    />
  );
}

export function PlatformInvitationsListPage() {
  const { accountId, actorRoleLevel, maxMembers, basePath } = usePlatformContext();
  return (
    <InvitationsListPage
      accountType="platform"
      accountId={accountId}
      slug="platform"
      actorRoleLevel={actorRoleLevel}
      maxMembers={maxMembers}
      basePath={basePath}
    />
  );
}

export function PlatformTransactionDetailPage() {
  const { basePath } = usePlatformContext();
  const { id } = useParams<{ id: string }>();
  return <TransactionDetailPage transactionId={id} basePath={basePath} />;
}

export function PlatformTransactionSettingsPage() {
  const { accountId, maxMembers } = usePlatformContext();
  return (
    <TransactionSettingsPage
      accountType="platform"
      accountId={accountId}
      slug="platform"
      maxMembers={maxMembers}
    />
  );
}
