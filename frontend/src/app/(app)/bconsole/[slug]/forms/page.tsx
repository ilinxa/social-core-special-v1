import { FeatureErrorBoundary } from "@/components/common/ErrorBoundary";
import { BusinessFormsDashboardPage } from "@/features/forms/components/FormsDashboardPage";

export default function Page() {
  return (
    <FeatureErrorBoundary>
      <BusinessFormsDashboardPage />
    </FeatureErrorBoundary>
  );
}
