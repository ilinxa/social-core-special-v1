"use client";

import { useParams } from "next/navigation";

import { useBusinessMemberships } from "@/stores/membership-store";
import { TemplateListPage } from "./TemplateListPage";
import { TemplateDetailPage } from "./TemplateDetailPage";
import { CreateTemplatePage } from "./CreateTemplatePage";
import { LibraryPage } from "./LibraryPage";
import { ResponsesPage } from "./ResponsesPage";
import { ResponseDetailPage } from "./ResponseDetailPage";

function useBusinessContext() {
  const { slug } = useParams<{ slug: string }>();
  const memberships = useBusinessMemberships();
  const myMembership = memberships.find((m) => m.account_slug === slug);
  const accountId = myMembership?.account_id ?? "";
  const basePath = `/bconsole/${slug}/forms`;
  return { slug, accountId, basePath };
}

export function BusinessTemplateListPage() {
  const { slug, accountId, basePath } = useBusinessContext();
  return (
    <TemplateListPage
      accountType="business"
      slug={slug}
      accountId={accountId}
      basePath={basePath}
    />
  );
}

export function BusinessTemplateDetailPage() {
  const { slug, accountId, basePath } = useBusinessContext();
  const { id } = useParams<{ id: string }>();
  return (
    <TemplateDetailPage
      accountType="business"
      accountId={accountId}
      formId={id}
      slug={slug}
      basePath={basePath}
    />
  );
}

export function BusinessCreateTemplatePage() {
  const { slug, accountId, basePath } = useBusinessContext();
  return (
    <CreateTemplatePage
      accountType="business"
      accountId={accountId}
      slug={slug}
      basePath={basePath}
    />
  );
}

export function BusinessLibraryPage() {
  const { slug, accountId, basePath } = useBusinessContext();
  return (
    <LibraryPage
      accountType="business"
      accountId={accountId}
      slug={slug}
      basePath={basePath}
    />
  );
}

export function BusinessResponsesPage() {
  const { slug, accountId, basePath } = useBusinessContext();
  return (
    <ResponsesPage
      accountType="business"
      accountId={accountId}
      slug={slug}
      basePath={basePath}
    />
  );
}

export function BusinessResponseDetailPage() {
  const { basePath } = useBusinessContext();
  const { id } = useParams<{ id: string }>();
  return <ResponseDetailPage responseId={id} basePath={basePath} />;
}
