import { FeatureErrorBoundary } from "@/components/common/ErrorBoundary";
import { PlatformResponseDetailPage } from "@/features/forms/components/PlatformFormPageWrappers";

export default function Page() {
  return (
    <FeatureErrorBoundary>
      <PlatformResponseDetailPage />
    </FeatureErrorBoundary>
  );
}
