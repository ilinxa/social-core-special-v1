"use client";

import { useParams } from "next/navigation";

import { TemplateCatalogPage } from "@/features/cms/components/TemplateCatalogPage";

export default function BusinessCmsCatalogPage() {
  const { slug } = useParams<{ slug: string }>();
  return <TemplateCatalogPage businessSlug={slug} />;
}
