"use client";

import { useParams } from "next/navigation";

import { PageEditor } from "@/features/cms/components/PageEditor";

export default function BusinessCmsPageEditorPage() {
  const { slug, siteSlug, pageSlug } = useParams<{
    slug: string;
    siteSlug: string;
    pageSlug: string;
  }>();
  return (
    <PageEditor
      context={{ type: "business", businessSlug: slug }}
      siteSlug={siteSlug}
      pageSlug={pageSlug}
      basePath={`/cconsole/${slug}/sites/${siteSlug}`}
    />
  );
}
