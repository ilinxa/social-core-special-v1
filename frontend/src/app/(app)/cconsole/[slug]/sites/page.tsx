"use client";

import { useParams } from "next/navigation";

import { SiteListPage } from "@/features/cms/components/SiteListPage";

export default function BusinessCmsSitesPage() {
  const { slug } = useParams<{ slug: string }>();
  return (
    <SiteListPage
      context={{ type: "business", businessSlug: slug }}
      basePath={`/cconsole/${slug}`}
    />
  );
}
