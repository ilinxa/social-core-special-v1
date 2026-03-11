import { FeatureErrorBoundary } from "@/components/common/ErrorBoundary";
import { BusinessRoleDetailPage } from "@/features/members/components/RoleDetailPage";

export default function Page() {
  return (
    <FeatureErrorBoundary>
      <BusinessRoleDetailPage />
    </FeatureErrorBoundary>
  );
}
