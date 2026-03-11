import { FeatureErrorBoundary } from "@/components/common/ErrorBoundary";
import { BusinessMemberDetailPage } from "@/features/members/components/MemberDetailPage";

export default function Page() {
  return (
    <FeatureErrorBoundary>
      <BusinessMemberDetailPage />
    </FeatureErrorBoundary>
  );
}
