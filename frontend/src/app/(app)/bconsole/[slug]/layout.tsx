"use client";

import { BusinessGuard } from "@/components/guards/BusinessGuard";

export default function BusinessLayout({ children }: { children: React.ReactNode }) {
  return <BusinessGuard>{children}</BusinessGuard>;
}
