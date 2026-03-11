import { FeatureErrorBoundary } from "@/components/common/ErrorBoundary";
import { BusinessTransactionsDashboardPage } from "@/features/transactions/components/TransactionsDashboardPage";

export default function Page() {
  return (
    <FeatureErrorBoundary>
      <BusinessTransactionsDashboardPage />
    </FeatureErrorBoundary>
  );
}
