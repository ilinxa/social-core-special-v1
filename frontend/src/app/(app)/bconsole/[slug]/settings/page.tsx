import { FeatureErrorBoundary } from "@/components/common/ErrorBoundary";
import { BusinessSettingsPage } from "@/features/settings/components/SettingsPage";

export default function Page() {
  return (
    <FeatureErrorBoundary>
      <BusinessSettingsPage />
    </FeatureErrorBoundary>
  );
}
