"use client";

import { SiteListPage } from "@/features/cms/components/SiteListPage";

export default function PlatformCmsSitesPage() {
  return <SiteListPage context={{ type: "platform" }} basePath="/cconsole" />;
}
