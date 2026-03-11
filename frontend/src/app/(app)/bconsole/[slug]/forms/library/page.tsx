import { FeatureErrorBoundary } from "@/components/common/ErrorBoundary";
import { BusinessLibraryPage } from "@/features/forms/components/BusinessFormPageWrappers";

export default function Page() {
  return (
    <FeatureErrorBoundary>
      <BusinessLibraryPage />
    </FeatureErrorBoundary>
  );
}
