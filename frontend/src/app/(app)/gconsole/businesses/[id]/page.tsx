"use client";

import { use } from "react";

import { GovernanceBusinessDetailPage } from "@/features/governance/components/GovernanceBusinessDetailPage";

export default function GconsoleBusinessDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);

  return <GovernanceBusinessDetailPage businessId={id} />;
}
