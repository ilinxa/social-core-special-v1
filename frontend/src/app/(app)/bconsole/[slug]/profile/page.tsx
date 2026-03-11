import { FeatureErrorBoundary } from "@/components/common/ErrorBoundary";
import { BusinessConsoleProfilePage } from "@/features/business/components/BusinessConsoleProfilePage";

export default function Page() {
  return (
    <FeatureErrorBoundary>
      <BusinessConsoleProfilePage />
    </FeatureErrorBoundary>
  );
}
