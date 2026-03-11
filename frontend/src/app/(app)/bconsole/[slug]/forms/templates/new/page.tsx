import { FeatureErrorBoundary } from "@/components/common/ErrorBoundary";
import { BusinessCreateTemplatePage } from "@/features/forms/components/BusinessFormPageWrappers";

export default function Page() {
  return (
    <FeatureErrorBoundary>
      <BusinessCreateTemplatePage />
    </FeatureErrorBoundary>
  );
}
