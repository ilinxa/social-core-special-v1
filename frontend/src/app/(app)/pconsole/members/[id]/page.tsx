import { FeatureErrorBoundary } from "@/components/common/ErrorBoundary";
import { MemberDetailPageInner } from "@/features/members/components/MemberDetailPage";

export default function Page() {
  return (
    <FeatureErrorBoundary>
      <PlatformMemberDetailPage />
    </FeatureErrorBoundary>
  );
}

function PlatformMemberDetailPage() {
  return (
    <MemberDetailPageInner
      accountType="platform"
      slug="platform"
      backUrl="/pconsole/members"
    />
  );
}
