import { FeatureErrorBoundary } from "@/components/common/ErrorBoundary";
import { BusinessTransactionSettingsPage } from "@/features/transactions/components/BusinessTransactionPageWrappers";

export default function Page() {
  return (
    <FeatureErrorBoundary>
      <BusinessTransactionSettingsPage />
    </FeatureErrorBoundary>
  );
}
