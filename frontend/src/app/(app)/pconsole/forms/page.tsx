import { FeatureErrorBoundary } from "@/components/common/ErrorBoundary";
import { PlatformFormsDashboardPage } from "@/features/forms/components/FormsDashboardPage";

export default function Page() {
  return (
    <FeatureErrorBoundary>
      <PlatformFormsDashboardPage />
    </FeatureErrorBoundary>
  );
}
