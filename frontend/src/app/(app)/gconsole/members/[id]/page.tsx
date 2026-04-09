"use client";

import { use } from "react";
import { GovernanceMemberDetailPage } from "@/features/governance/components/GovernanceMemberDetailPage";

export default function Page({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  return <GovernanceMemberDetailPage memberId={id} />;
}
