"use client";

import { useParams } from "next/navigation";

import { usePlatformMembership } from "@/stores/membership-store";
import { TemplateListPage } from "./TemplateListPage";
import { TemplateDetailPage } from "./TemplateDetailPage";
import { CreateTemplatePage } from "./CreateTemplatePage";
import { LibraryPage } from "./LibraryPage";
import { ResponsesPage } from "./ResponsesPage";
import { ResponseDetailPage } from "./ResponseDetailPage";

const PLATFORM_BASE_PATH = "/pconsole/forms";

function usePlatformContext() {
  const myMembership = usePlatformMembership();
  const accountId = myMembership?.account_id ?? "";
  return { accountId, basePath: PLATFORM_BASE_PATH };
}

export function PlatformTemplateListPage() {
  const { accountId, basePath } = usePlatformContext();
  return (
    <TemplateListPage
      accountType="platform"
      slug="platform"
      accountId={accountId}
      basePath={basePath}
    />
  );
}

export function PlatformTemplateDetailPage() {
  const { accountId, basePath } = usePlatformContext();
  const { id } = useParams<{ id: string }>();
  return (
    <TemplateDetailPage
      accountType="platform"
      accountId={accountId}
      formId={id}
      slug="platform"
      basePath={basePath}
    />
  );
}

export function PlatformCreateTemplatePage() {
  const { accountId, basePath } = usePlatformContext();
  return (
    <CreateTemplatePage
      accountType="platform"
      accountId={accountId}
      slug="platform"
      basePath={basePath}
    />
  );
}

export function PlatformLibraryPage() {
  const { accountId, basePath } = usePlatformContext();
  return (
    <LibraryPage
      accountType="platform"
      accountId={accountId}
      slug="platform"
      basePath={basePath}
    />
  );
}

export function PlatformResponsesPage() {
  const { accountId, basePath } = usePlatformContext();
  return (
    <ResponsesPage
      accountType="platform"
      accountId={accountId}
      slug="platform"
      basePath={basePath}
    />
  );
}

export function PlatformResponseDetailPage() {
  const { basePath } = usePlatformContext();
  const { id } = useParams<{ id: string }>();
  return <ResponseDetailPage responseId={id} basePath={basePath} />;
}
