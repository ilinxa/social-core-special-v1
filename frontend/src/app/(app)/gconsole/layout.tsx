"use client";

import { GovernanceGuard } from "@/components/guards/GovernanceGuard";

export default function GconsoleLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <GovernanceGuard>{children}</GovernanceGuard>;
}
