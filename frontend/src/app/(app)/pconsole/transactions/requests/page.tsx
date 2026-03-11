import { FeatureErrorBoundary } from "@/components/common/ErrorBoundary";
import { PlatformRequestsListPage } from "@/features/transactions/components/PlatformTransactionPageWrappers";

export default function Page() {
  return (
    <FeatureErrorBoundary>
      <PlatformRequestsListPage />
    </FeatureErrorBoundary>
  );
}
