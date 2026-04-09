import { FeatureErrorBoundary } from "@/components/common/ErrorBoundary";
import { NotificationsPage } from "@/features/notifications/components/NotificationsPage";

export default function Page() {
  return (
    <FeatureErrorBoundary>
      <NotificationsPage />
    </FeatureErrorBoundary>
  );
}
