"use client";

import { useState } from "react";
import Link from "next/link";
import { Building2, Search, Users } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { useGovernanceBusinesses } from "@/features/governance/hooks/use-governance-queries";
import type { GovernanceBusiness } from "@/types/governance";

const STATUS_OPTIONS = [
  { value: "all", label: "All Statuses" },
  { value: "pending", label: "Pending" },
  { value: "active", label: "Active" },
  { value: "suspended", label: "Suspended" },
  { value: "archived", label: "Archived" },
];

const VERIFICATION_OPTIONS = [
  { value: "all", label: "All Verification" },
  { value: "unverified", label: "Unverified" },
  { value: "pending", label: "Pending" },
  { value: "verified", label: "Verified" },
  { value: "rejected", label: "Rejected" },
];

function statusBadgeVariant(
  status: string,
): "default" | "secondary" | "destructive" | "outline" {
  switch (status) {
    case "active":
      return "default";
    case "suspended":
      return "destructive";
    case "archived":
      return "secondary";
    case "pending":
      return "outline";
    default:
      return "secondary";
  }
}

export function GovernanceBusinessesPage() {
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("all");
  const [verification, setVerification] = useState("all");
  const [page, setPage] = useState(1);

  const params: Record<string, unknown> = { page, page_size: 20 };
  if (search.trim()) params.search = search.trim();
  if (status !== "all") params.status = status;
  if (verification !== "all") params.verification_status = verification;

  const { data, isLoading } = useGovernanceBusinesses(params);

  function handleSearchChange(value: string) {
    setSearch(value);
    setPage(1);
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">Business Governance</h1>

      {/* Filter bar */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <Search className="text-muted-foreground absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2" />
          <Input
            placeholder="Search by business name..."
            value={search}
            onChange={(e) => handleSearchChange(e.target.value)}
            className="pl-9"
          />
        </div>
        <Select
          value={status}
          onValueChange={(v) => {
            setStatus(v);
            setPage(1);
          }}
        >
          <SelectTrigger className="w-[160px]">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            {STATUS_OPTIONS.map((opt) => (
              <SelectItem key={opt.value} value={opt.value}>
                {opt.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select
          value={verification}
          onValueChange={(v) => {
            setVerification(v);
            setPage(1);
          }}
        >
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Verification" />
          </SelectTrigger>
          <SelectContent>
            {VERIFICATION_OPTIONS.map((opt) => (
              <SelectItem key={opt.value} value={opt.value}>
                {opt.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Results */}
      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-20 w-full rounded-lg" />
          ))}
        </div>
      ) : !data?.results.length ? (
        <div className="text-muted-foreground py-12 text-center">
          {search || status !== "all" || verification !== "all"
            ? "No businesses match your filters."
            : "No businesses found."}
        </div>
      ) : (
        <>
          <p className="text-muted-foreground text-sm">
            {data.count} {data.count === 1 ? "business" : "businesses"}
          </p>
          <div className="space-y-2">
            {data.results.map((biz) => (
              <BusinessCard key={biz.id} business={biz} />
            ))}
          </div>

          {(data.previous || data.next) && (
            <div className="flex items-center justify-between pt-2">
              <Button
                variant="outline"
                size="sm"
                disabled={!data.previous}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                Previous
              </Button>
              <span className="text-muted-foreground text-sm">Page {page}</span>
              <Button
                variant="outline"
                size="sm"
                disabled={!data.next}
                onClick={() => setPage((p) => p + 1)}
              >
                Next
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function BusinessCard({ business }: { business: GovernanceBusiness }) {
  return (
    <Link
      href={`/gconsole/businesses/${business.id}`}
      className="hover:bg-muted/50 flex items-center gap-4 rounded-lg border p-4 transition-colors"
    >
      <div className="bg-muted flex h-10 w-10 items-center justify-center rounded-lg">
        <Building2 className="text-muted-foreground h-5 w-5" />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <p className="truncate font-medium">{business.legal_name}</p>
          <Badge variant={statusBadgeVariant(business.status)}>
            {business.status_display}
          </Badge>
          {business.verification_status === "verified" && (
            <Badge variant="outline">Verified</Badge>
          )}
        </div>
        <p className="text-muted-foreground text-sm">
          {business.business_type_display} &middot; {business.country}
          {business.city ? `, ${business.city}` : ""}
        </p>
      </div>
      <div className="text-muted-foreground hidden items-center gap-1 text-sm sm:flex">
        <Users className="h-4 w-4" />
        <span>{business.member_count}</span>
      </div>
    </Link>
  );
}
