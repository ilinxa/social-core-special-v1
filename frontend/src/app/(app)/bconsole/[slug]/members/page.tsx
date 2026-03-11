import { FeatureErrorBoundary } from "@/components/common/ErrorBoundary";
import { BusinessMemberDashboardPage } from "@/features/members/components/MemberDashboardPage";

export default function Page() {
  return (
    <FeatureErrorBoundary>
      <BusinessMemberDashboardPage />
    </FeatureErrorBoundary>
  );
}
