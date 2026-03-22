import type { Metadata } from "next";

import { BusinessDiscoveryPage } from "@/features/business/components/BusinessDiscoveryPage";

export const metadata: Metadata = { title: "Business Profile" };

export default function Page() {
  return <BusinessDiscoveryPage />;
}
