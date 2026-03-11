import { FeatureErrorBoundary } from "@/components/common/ErrorBoundary";
import { BusinessResponseDetailPage } from "@/features/forms/components/BusinessFormPageWrappers";

export default function Page() {
  return (
    <FeatureErrorBoundary>
      <BusinessResponseDetailPage />
    </FeatureErrorBoundary>
  );
}
