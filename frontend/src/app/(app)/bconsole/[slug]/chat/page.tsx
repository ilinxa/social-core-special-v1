"use client";

import { useParams } from "next/navigation";

import { FeatureErrorBoundary } from "@/components/common/ErrorBoundary";
import { ChatPage } from "@/features/chat/components/ChatPage";
import { useBusinessMemberships } from "@/stores/membership-store";

export default function Page() {
  const { slug } = useParams<{ slug: string }>();
  const memberships = useBusinessMemberships();
  const membership = memberships.find((m) => m.account_slug === slug);
  const businessId = membership?.account_id ?? null;

  return (
    <FeatureErrorBoundary>
      <ChatPage
        scope={{
          scopeType: "business",
          scopeId: businessId,
          slug,
          participantType: "business",
          participantId: businessId ?? undefined,
        }}
        showEntityInbox
      />
    </FeatureErrorBoundary>
  );
}
