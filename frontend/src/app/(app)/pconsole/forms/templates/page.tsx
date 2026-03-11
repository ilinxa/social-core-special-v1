import { FeatureErrorBoundary } from "@/components/common/ErrorBoundary";
import { PlatformTemplateListPage } from "@/features/forms/components/PlatformFormPageWrappers";

export default function Page() {
  return (
    <FeatureErrorBoundary>
      <PlatformTemplateListPage />
    </FeatureErrorBoundary>
  );
}
