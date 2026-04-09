"use client";

import Link from "next/link";
import {
  ArrowRightLeft,
  Building2,
  FileCheck,
  Shield,
  Users,
} from "lucide-react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useGovernanceBusinesses,
  useGovernanceVerification,
} from "@/features/governance/hooks/use-governance-queries";

export function GovernanceDashboardPage() {
  const { data: activeData, isLoading: activeLoading } =
    useGovernanceBusinesses({ status: "active", page_size: 1 });
  const { data: suspendedData, isLoading: suspendedLoading } =
    useGovernanceBusinesses({ status: "suspended", page_size: 1 });
  const { data: verificationData, isLoading: verificationLoading } =
    useGovernanceVerification({ page_size: 1 });

  return (
    <div className="space-y-8">
      <div className="flex items-center gap-3">
        <Shield className="h-7 w-7" />
        <h1 className="text-2xl font-bold tracking-tight">
          Governance Console
        </h1>
      </div>

      {/* Summary cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <SummaryCard
          title="Active Businesses"
          value={activeData?.count}
          isLoading={activeLoading}
          href="/gconsole/businesses?status=active"
          icon={<Building2 className="h-5 w-5" />}
        />
        <SummaryCard
          title="Suspended Businesses"
          value={suspendedData?.count}
          isLoading={suspendedLoading}
          href="/gconsole/businesses?status=suspended"
          icon={<Building2 className="h-5 w-5" />}
          highlight={!!suspendedData?.count && suspendedData.count > 0}
        />
        <SummaryCard
          title="Pending Verifications"
          value={verificationData?.count}
          isLoading={verificationLoading}
          href="/gconsole/verification"
          icon={<FileCheck className="h-5 w-5" />}
          highlight={
            !!verificationData?.count && verificationData.count > 0
          }
        />
      </div>

      {/* Quick links */}
      <div>
        <h2 className="mb-4 text-lg font-semibold">Quick Access</h2>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <QuickLinkCard
            title="Businesses"
            description="View and manage all businesses"
            href="/gconsole/businesses"
            icon={<Building2 className="h-5 w-5" />}
          />
          <QuickLinkCard
            title="Members"
            description="Cross-account member search and enforcement"
            href="/gconsole/members"
            icon={<Users className="h-5 w-5" />}
          />
          <QuickLinkCard
            title="Audit Log"
            description="View governance audit trail"
            href="/gconsole/audit"
            icon={<Shield className="h-5 w-5" />}
          />
          <QuickLinkCard
            title="Transactions"
            description="Global transaction overview"
            href="/gconsole/transactions"
            icon={<ArrowRightLeft className="h-5 w-5" />}
          />
          <QuickLinkCard
            title="Verification"
            description="Review pending verification requests"
            href="/gconsole/verification"
            icon={<FileCheck className="h-5 w-5" />}
          />
        </div>
      </div>
    </div>
  );
}

function SummaryCard({
  title,
  value,
  isLoading,
  href,
  icon,
  highlight = false,
}: {
  title: string;
  value: number | undefined;
  isLoading: boolean;
  href: string;
  icon: React.ReactNode;
  highlight?: boolean;
}) {
  return (
    <Link href={href}>
      <Card
        className={`transition-colors hover:bg-muted/50 ${highlight ? "border-amber-500/50" : ""}`}
      >
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <CardTitle className="text-sm font-medium">{title}</CardTitle>
          <div className="text-muted-foreground">{icon}</div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <Skeleton className="h-8 w-16" />
          ) : (
            <p className="text-3xl font-bold">{value ?? 0}</p>
          )}
        </CardContent>
      </Card>
    </Link>
  );
}

function QuickLinkCard({
  title,
  description,
  href,
  icon,
}: {
  title: string;
  description: string;
  href: string;
  icon: React.ReactNode;
}) {
  return (
    <Link href={href}>
      <Card className="h-full transition-colors hover:bg-muted/50">
        <CardHeader className="pb-2">
          <div className="text-muted-foreground mb-2">{icon}</div>
          <CardTitle className="text-base">{title}</CardTitle>
          <CardDescription>{description}</CardDescription>
        </CardHeader>
      </Card>
    </Link>
  );
}
