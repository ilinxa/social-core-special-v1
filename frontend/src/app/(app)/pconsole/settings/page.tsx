import { FeatureErrorBoundary } from "@/components/common/ErrorBoundary";
import { PlatformSettingsPage } from "@/features/settings/components/SettingsPage";

export default function Page() {
  return (
    <FeatureErrorBoundary>
      <PlatformSettingsPage />
    </FeatureErrorBoundary>
  );
}
