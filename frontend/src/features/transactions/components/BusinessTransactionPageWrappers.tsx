"use client";

import { useParams } from "next/navigation";

import { useBusinessMemberships } from "@/stores/membership-store";
import { RequestsListPage } from "./RequestsListPage";
import { InvitationsListPage } from "./InvitationsListPage";
import { TransactionDetailPage } from "./TransactionDetailPage";
import { TransactionSettingsPage } from "./TransactionSettingsPage";

function useBusinessContext() {
  const { slug } = useParams<{ slug: string }>();
  const memberships = useBusinessMemberships();
  const myMembership = memberships.find((m) => m.account_slug === slug);
  const accountId = myMembership?.account_id ?? "";
  const actorRoleLevel = myMembership?.role?.level ?? 999;
  const maxMembers = myMembership?.account_max_members ?? 0;
  const basePath = `/bconsole/${slug}/transactions`;
  return { slug, accountId, actorRoleLevel, maxMembers, basePath };
}

export function BusinessRequestsListPage() {
  const { accountId, basePath } = useBusinessContext();
  return (
    <RequestsListPage
      accountType="business"
      accountId={accountId}
      basePath={basePath}
    />
  );
}

export function BusinessInvitationsListPage() {
  const { slug, accountId, actorRoleLevel, maxMembers, basePath } = useBusinessContext();
  return (
    <InvitationsListPage
      accountType="business"
      accountId={accountId}
      slug={slug}
      actorRoleLevel={actorRoleLevel}
      maxMembers={maxMembers}
      basePath={basePath}
    />
  );
}

export function BusinessTransactionDetailPage() {
  const { basePath } = useBusinessContext();
  const { id } = useParams<{ id: string }>();
  return <TransactionDetailPage transactionId={id} basePath={basePath} />;
}

export function BusinessTransactionSettingsPage() {
  const { slug, accountId, maxMembers } = useBusinessContext();
  return (
    <TransactionSettingsPage
      accountType="business"
      accountId={accountId}
      slug={slug}
      maxMembers={maxMembers}
    />
  );
}
