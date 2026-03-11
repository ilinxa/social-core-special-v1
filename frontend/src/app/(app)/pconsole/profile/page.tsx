import { FeatureErrorBoundary } from "@/components/common/ErrorBoundary";
import { PlatformConsoleProfilePage } from "@/features/platform/components/PlatformConsoleProfilePage";

export default function Page() {
  return (
    <FeatureErrorBoundary>
      <PlatformConsoleProfilePage />
    </FeatureErrorBoundary>
  );
}
