import { FeatureErrorBoundary } from "@/components/common/ErrorBoundary";
import { PlatformTransactionDetailPage } from "@/features/transactions/components/PlatformTransactionPageWrappers";

export default function Page() {
  return (
    <FeatureErrorBoundary>
      <PlatformTransactionDetailPage />
    </FeatureErrorBoundary>
  );
}
