import { FeatureErrorBoundary } from "@/components/common/ErrorBoundary";
import { BusinessTemplateDetailPage } from "@/features/forms/components/BusinessFormPageWrappers";

export default function Page() {
  return (
    <FeatureErrorBoundary>
      <BusinessTemplateDetailPage />
    </FeatureErrorBoundary>
  );
}
