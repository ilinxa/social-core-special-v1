import { FeatureErrorBoundary } from "@/components/common/ErrorBoundary";
import { BusinessFollowersPage } from "@/features/network/components/BusinessFollowersPage";

export default function Page() {
  return (
    <FeatureErrorBoundary>
      <BusinessFollowersPage />
    </FeatureErrorBoundary>
  );
}
