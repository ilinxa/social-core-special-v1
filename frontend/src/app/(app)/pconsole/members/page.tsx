import { FeatureErrorBoundary } from "@/components/common/ErrorBoundary";
import { PlatformMemberDashboardPage } from "@/features/members/components/PlatformMemberDashboardPage";

export default function Page() {
  return (
    <FeatureErrorBoundary>
      <PlatformMemberDashboardPage />
    </FeatureErrorBoundary>
  );
}
