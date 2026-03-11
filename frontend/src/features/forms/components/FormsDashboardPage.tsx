"use client";

import { useParams } from "next/navigation";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Can } from "@/components/common/Can";
import { useHasPermission } from "@/hooks/use-has-permission";
import {
  useBusinessMemberships,
  usePlatformMembership,
} from "@/stores/membership-store";
import type { AccountType } from "@/types/rbac";

type FormsDashboardPageInnerProps = {
  accountType: AccountType;
  slug: string;
  accountId: string;
  basePath: string;
};

function FormsDashboardPageInner({
  accountType,
  slug,
  accountId,
  basePath,
}: FormsDashboardPageInnerProps) {
  const router = useRouter();
  const canCreateForm = useHasPermission("can_create_form", accountType, accountId);
  const canViewResponses = useHasPermission("can_view_responses", accountType, accountId);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">Forms</h1>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <Card
          className="cursor-pointer transition-colors hover:bg-muted/50"
          onClick={() => router.push(`${basePath}/templates`)}
        >
          <CardHeader>
            <CardTitle className="text-base">Templates</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Create and manage form templates for your organization.
            </p>
          </CardContent>
        </Card>

        <Card
          className="cursor-pointer transition-colors hover:bg-muted/50"
          onClick={() => router.push(`${basePath}/library`)}
        >
          <CardHeader>
            <CardTitle className="text-base">Library</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Browse and fork public form templates.
            </p>
          </CardContent>
        </Card>

        <Can allowed={canViewResponses}>
          <Card
            className="cursor-pointer transition-colors hover:bg-muted/50"
            onClick={() => router.push(`${basePath}/responses`)}
          >
            <CardHeader>
              <CardTitle className="text-base">Responses</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                View and manage form submissions.
              </p>
            </CardContent>
          </Card>
        </Can>
      </div>

      <Can allowed={canCreateForm}>
        <Button onClick={() => router.push(`${basePath}/templates/new`)}>
          Create New Form
        </Button>
      </Can>
    </div>
  );
}

// =============================================================================
// BUSINESS WRAPPER
// =============================================================================

export function BusinessFormsDashboardPage() {
  const { slug } = useParams<{ slug: string }>();
  const memberships = useBusinessMemberships();
  const myMembership = memberships.find((m) => m.account_slug === slug);
  const accountId = myMembership?.account_id ?? "";

  return (
    <FormsDashboardPageInner
      accountType="business"
      slug={slug}
      accountId={accountId}
      basePath={`/bconsole/${slug}/forms`}
    />
  );
}

// =============================================================================
// PLATFORM WRAPPER
// =============================================================================

export function PlatformFormsDashboardPage() {
  const myMembership = usePlatformMembership();
  const accountId = myMembership?.account_id ?? "";

  return (
    <FormsDashboardPageInner
      accountType="platform"
      slug="platform"
      accountId={accountId}
      basePath="/pconsole/forms"
    />
  );
}
