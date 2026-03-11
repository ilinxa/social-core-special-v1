import { FeatureErrorBoundary } from "@/components/common/ErrorBoundary";
import { PlatformLibraryPage } from "@/features/forms/components/PlatformFormPageWrappers";

export default function Page() {
  return (
    <FeatureErrorBoundary>
      <PlatformLibraryPage />
    </FeatureErrorBoundary>
  );
}
