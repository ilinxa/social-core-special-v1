"use client";

import { CmsBusinessGuard } from "@/components/guards/CmsBusinessGuard";

export default function CmsBusinessLayout({ children }: { children: React.ReactNode }) {
  return <CmsBusinessGuard>{children}</CmsBusinessGuard>;
}
