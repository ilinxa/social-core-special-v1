import { FeatureErrorBoundary } from "@/components/common/ErrorBoundary";
import { BusinessInvitationsListPage } from "@/features/transactions/components/BusinessTransactionPageWrappers";

export default function Page() {
  return (
    <FeatureErrorBoundary>
      <BusinessInvitationsListPage />
    </FeatureErrorBoundary>
  );
}
