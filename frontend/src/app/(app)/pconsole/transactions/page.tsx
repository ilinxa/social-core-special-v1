import { FeatureErrorBoundary } from "@/components/common/ErrorBoundary";
import { PlatformTransactionsDashboardPage } from "@/features/transactions/components/TransactionsDashboardPage";

export default function Page() {
  return (
    <FeatureErrorBoundary>
      <PlatformTransactionsDashboardPage />
    </FeatureErrorBoundary>
  );
}
