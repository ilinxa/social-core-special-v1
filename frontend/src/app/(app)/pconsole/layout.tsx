"use client";

import { PlatformGuard } from "@/components/guards/PlatformGuard";

export default function PlatformLayout({ children }: { children: React.ReactNode }) {
  return <PlatformGuard>{children}</PlatformGuard>;
}
