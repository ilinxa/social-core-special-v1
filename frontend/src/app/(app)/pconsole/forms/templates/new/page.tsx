import { FeatureErrorBoundary } from "@/components/common/ErrorBoundary";
import { PlatformCreateTemplatePage } from "@/features/forms/components/PlatformFormPageWrappers";

export default function Page() {
  return (
    <FeatureErrorBoundary>
      <PlatformCreateTemplatePage />
    </FeatureErrorBoundary>
  );
}
