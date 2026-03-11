import { FeatureErrorBoundary } from "@/components/common/ErrorBoundary";
import { BusinessTemplateListPage } from "@/features/forms/components/BusinessFormPageWrappers";

export default function Page() {
  return (
    <FeatureErrorBoundary>
      <BusinessTemplateListPage />
    </FeatureErrorBoundary>
  );
}
