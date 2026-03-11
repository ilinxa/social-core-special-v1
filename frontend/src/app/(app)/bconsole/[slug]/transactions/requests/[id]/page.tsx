import { FeatureErrorBoundary } from "@/components/common/ErrorBoundary";
import { BusinessTransactionDetailPage } from "@/features/transactions/components/BusinessTransactionPageWrappers";

export default function Page() {
  return (
    <FeatureErrorBoundary>
      <BusinessTransactionDetailPage />
    </FeatureErrorBoundary>
  );
}
