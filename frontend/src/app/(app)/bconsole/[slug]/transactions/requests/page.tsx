import { FeatureErrorBoundary } from "@/components/common/ErrorBoundary";
import { BusinessRequestsListPage } from "@/features/transactions/components/BusinessTransactionPageWrappers";

export default function Page() {
  return (
    <FeatureErrorBoundary>
      <BusinessRequestsListPage />
    </FeatureErrorBoundary>
  );
}
