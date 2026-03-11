import { FeatureErrorBoundary } from "@/components/common/ErrorBoundary";
import { PlatformTransactionSettingsPage } from "@/features/transactions/components/PlatformTransactionPageWrappers";

export default function Page() {
  return (
    <FeatureErrorBoundary>
      <PlatformTransactionSettingsPage />
    </FeatureErrorBoundary>
  );
}
