import { FeatureErrorBoundary } from "@/components/common/ErrorBoundary";
import { ChatPage } from "@/features/chat/components/ChatPage";

export default function Page() {
  return (
    <FeatureErrorBoundary>
      <ChatPage scope={{ scopeType: "global", scopeId: null }} />
    </FeatureErrorBoundary>
  );
}
