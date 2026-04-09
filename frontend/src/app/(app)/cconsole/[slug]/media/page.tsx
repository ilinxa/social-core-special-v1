"use client";

import { useParams } from "next/navigation";

import { MediaLibraryPage } from "@/features/cms/components/MediaLibraryPage";

export default function BusinessCmsMediaPage() {
  const { slug } = useParams<{ slug: string }>();
  return <MediaLibraryPage context={{ type: "business", businessSlug: slug }} />;
}
