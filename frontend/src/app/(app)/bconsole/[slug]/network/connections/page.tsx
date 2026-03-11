import { FeatureErrorBoundary } from "@/components/common/ErrorBoundary";
import { BusinessConnectionsPage } from "@/features/network/components/BusinessConnectionsPage";

export default function Page() {
  return (
    <FeatureErrorBoundary>
      <BusinessConnectionsPage />
    </FeatureErrorBoundary>
  );
}
