"use client";

import { PlatformGuard } from "@/components/guards/PlatformGuard";

export default function CmsPlatformLayout({ children }: { children: React.ReactNode }) {
  return <PlatformGuard>{children}</PlatformGuard>;
}
