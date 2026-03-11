import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { FeatureErrorBoundary } from "@/components/common/ErrorBoundary";
import { ChangePasswordForm } from "@/features/auth/components/ChangePasswordForm";
import { SessionList } from "@/features/auth/components/SessionList";

export default function SessionsPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Security</h1>
      <FeatureErrorBoundary>
        <Card>
          <CardHeader>
            <CardTitle>Active Sessions</CardTitle>
          </CardHeader>
          <CardContent>
            <SessionList />
          </CardContent>
        </Card>
      </FeatureErrorBoundary>
      <FeatureErrorBoundary>
        <Card>
          <CardHeader>
            <CardTitle>Change Password</CardTitle>
          </CardHeader>
          <CardContent>
            <ChangePasswordForm />
          </CardContent>
        </Card>
      </FeatureErrorBoundary>
    </div>
  );
}
