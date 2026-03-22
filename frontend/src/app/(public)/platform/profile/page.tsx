import type { Metadata } from "next";

import { PlatformPublicProfilePage } from "@/features/platform/components/PlatformPublicProfilePage";

export const metadata: Metadata = { title: "Platform Profile" };

export default function Page() {
  return <PlatformPublicProfilePage />;
}
