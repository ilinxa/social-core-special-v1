import { FeatureErrorBoundary } from "@/components/common/ErrorBoundary";
import { PlatformResponsesPage } from "@/features/forms/components/PlatformFormPageWrappers";

export default function Page() {
  return (
    <FeatureErrorBoundary>
      <PlatformResponsesPage />
    </FeatureErrorBoundary>
  );
}
