import { FeatureErrorBoundary } from "@/components/common/ErrorBoundary";
import { PlatformInvitationsListPage } from "@/features/transactions/components/PlatformTransactionPageWrappers";

export default function Page() {
  return (
    <FeatureErrorBoundary>
      <PlatformInvitationsListPage />
    </FeatureErrorBoundary>
  );
}
