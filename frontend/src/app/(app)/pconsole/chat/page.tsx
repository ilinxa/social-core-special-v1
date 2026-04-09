"use client";

import { FeatureErrorBoundary } from "@/components/common/ErrorBoundary";
import { ChatPage } from "@/features/chat/components/ChatPage";
import { usePlatformMembership } from "@/stores/membership-store";

export default function Page() {
  const membership = usePlatformMembership();
  const platformId = membership?.account_id ?? null;

  return (
    <FeatureErrorBoundary>
      <ChatPage
        scope={{
          scopeType: "platform",
          scopeId: platformId,
          participantType: "platform",
          participantId: platformId ?? undefined,
        }}
        showEntityInbox
      />
    </FeatureErrorBoundary>
  );
}
