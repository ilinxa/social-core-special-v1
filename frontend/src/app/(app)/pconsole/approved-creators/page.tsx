import { FeatureErrorBoundary } from "@/components/common/ErrorBoundary";
import { ApprovedCreatorsPage } from "@/features/users/components/ApprovedCreatorsPage";

export default function Page() {
  return (
    <FeatureErrorBoundary>
      <ApprovedCreatorsPage />
    </FeatureErrorBoundary>
  );
}
