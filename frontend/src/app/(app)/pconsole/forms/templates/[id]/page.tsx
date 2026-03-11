import { FeatureErrorBoundary } from "@/components/common/ErrorBoundary";
import { PlatformTemplateDetailPage } from "@/features/forms/components/PlatformFormPageWrappers";

export default function Page() {
  return (
    <FeatureErrorBoundary>
      <PlatformTemplateDetailPage />
    </FeatureErrorBoundary>
  );
}
