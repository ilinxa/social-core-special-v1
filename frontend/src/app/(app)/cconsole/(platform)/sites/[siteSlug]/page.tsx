"use client";

import { useParams } from "next/navigation";

import { SiteDetailPage } from "@/features/cms/components/SiteDetailPage";

export default function PlatformCmsSiteDetailPage() {
  const { siteSlug } = useParams<{ siteSlug: string }>();
  return (
    <SiteDetailPage
      context={{ type: "platform" }}
      siteSlug={siteSlug}
      basePath="/cconsole"
    />
  );
}
