/**
 * CMS Access Gate
 * ================
 * Inner component (NOT a layout guard) for business CMS pages.
 * Checks whether CMS is enabled for the current business.
 *
 * If CMS is disabled → shows CmsActivationPage instead of children.
 * If CMS is enabled → renders children normally.
 *
 * Uses the feature gate handler: on first API call, if 403 feature_disabled
 * is returned, the gate records it and this component reactively hides content.
 */

"use client";

import { useParams } from "next/navigation";

import { useCmsFeatureEnabled } from "@/features/cms/hooks/use-cms-feature-gate";
import { CmsActivationPage } from "@/features/cms/components/CmsActivationPage";

interface CmsAccessGateProps {
  children: React.ReactNode;
}

export function CmsAccessGate({ children }: CmsAccessGateProps) {
  const params = useParams<{ slug: string }>();
  const businessSlug = params?.slug ?? "";
  const cmsEnabled = useCmsFeatureEnabled("business_cms");

  if (!cmsEnabled) {
    return <CmsActivationPage businessSlug={businessSlug} />;
  }

  return <>{children}</>;
}
