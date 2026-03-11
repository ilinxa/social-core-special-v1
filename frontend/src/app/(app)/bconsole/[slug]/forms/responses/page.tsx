import { FeatureErrorBoundary } from "@/components/common/ErrorBoundary";
import { BusinessResponsesPage } from "@/features/forms/components/BusinessFormPageWrappers";

export default function Page() {
  return (
    <FeatureErrorBoundary>
      <BusinessResponsesPage />
    </FeatureErrorBoundary>
  );
}
