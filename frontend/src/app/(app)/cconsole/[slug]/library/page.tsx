"use client";

import { useParams } from "next/navigation";

import { TemplateLibraryPage } from "@/features/cms/components/TemplateLibraryPage";

export default function BusinessCmsLibraryPage() {
  const { slug } = useParams<{ slug: string }>();
  return <TemplateLibraryPage businessSlug={slug} />;
}
