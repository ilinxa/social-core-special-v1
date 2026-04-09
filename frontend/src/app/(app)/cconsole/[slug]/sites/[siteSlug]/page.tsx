"use client";

import { useParams } from "next/navigation";

import { SiteDetailPage } from "@/features/cms/components/SiteDetailPage";

export default function BusinessCmsSiteDetailPage() {
  const { slug, siteSlug } = useParams<{ slug: string; siteSlug: string }>();
  return (
    <SiteDetailPage
      context={{ type: "business", businessSlug: slug }}
      siteSlug={siteSlug}
      basePath={`/cconsole/${slug}`}
    />
  );
}
