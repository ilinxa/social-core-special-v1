import { FeatureErrorBoundary } from "@/components/common/ErrorBoundary";
import { RoleDetailPageInner } from "@/features/members/components/RoleDetailPage";

export default function Page() {
  return (
    <FeatureErrorBoundary>
      <PlatformRoleDetailPage />
    </FeatureErrorBoundary>
  );
}

function PlatformRoleDetailPage() {
  return (
    <RoleDetailPageInner
      accountType="platform"
      slug="platform"
      backUrl="/pconsole/members"
    />
  );
}
