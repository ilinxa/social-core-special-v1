"use client";

import { useParams } from "next/navigation";

import { PageEditor } from "@/features/cms/components/PageEditor";

export default function PlatformCmsPageEditorPage() {
  const { siteSlug, pageSlug } = useParams<{
    siteSlug: string;
    pageSlug: string;
  }>();
  return (
    <PageEditor
      context={{ type: "platform" }}
      siteSlug={siteSlug}
      pageSlug={pageSlug}
      basePath={`/cconsole/sites/${siteSlug}`}
    />
  );
}
