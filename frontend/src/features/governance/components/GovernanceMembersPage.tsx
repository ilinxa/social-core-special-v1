"use client";

import { useState } from "react";
import Link from "next/link";
import { Search } from "lucide-react";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
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
import { useGovernanceMembers } from "@/features/governance/hooks/use-governance-queries";
import type { GovernanceMember } from "@/types/governance";

const ACCOUNT_TYPE_OPTIONS = [
  { value: "all", label: "All Accounts" },
  { value: "business", label: "Business" },
  { value: "platform", label: "Platform" },
];

const STATUS_OPTIONS = [
  { value: "all", label: "All Statuses" },
  { value: "active", label: "Active" },
  { value: "suspended", label: "Suspended" },
  { value: "banned", label: "Banned" },
  { value: "removed", label: "Removed" },
];

function statusBadgeVariant(
  status: string,
): "default" | "secondary" | "destructive" | "outline" {
  switch (status) {
    case "active":
      return "default";
    case "suspended":
      return "outline";
    case "banned":
      return "destructive";
    case "removed":
      return "secondary";
    default:
      return "secondary";
  }
}

export function GovernanceMembersPage() {
  const [search, setSearch] = useState("");
  const [accountType, setAccountType] = useState("all");
  const [status, setStatus] = useState("all");
  const [page, setPage] = useState(1);

  const params: Record<string, unknown> = { page, page_size: 20 };
  if (search.trim()) params.search = search.trim();
  if (accountType !== "all") params.account_type = accountType;
  if (status !== "all") params.status = status;

  const { data, isLoading } = useGovernanceMembers(params);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">Member Governance</h1>

      {/* Filter bar */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <Search className="text-muted-foreground absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2" />
          <Input
            placeholder="Search by email, username, or name..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            className="pl-9"
          />
        </div>
        <Select
          value={accountType}
          onValueChange={(v) => {
            setAccountType(v);
            setPage(1);
          }}
        >
          <SelectTrigger className="w-[160px]">
            <SelectValue placeholder="Account" />
          </SelectTrigger>
          <SelectContent>
            {ACCOUNT_TYPE_OPTIONS.map((opt) => (
              <SelectItem key={opt.value} value={opt.value}>
                {opt.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
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
          {search || accountType !== "all" || status !== "all"
            ? "No members match your filters."
            : "No members found."}
        </div>
      ) : (
        <>
          <p className="text-muted-foreground text-sm">
            {data.count} {data.count === 1 ? "member" : "members"}
          </p>
          <div className="space-y-2">
            {data.results.map((member) => (
              <MemberCard key={member.id} member={member} />
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

function MemberCard({ member }: { member: GovernanceMember }) {
  const initials = member.user.display_name
    ? member.user.display_name
        .split(" ")
        .map((n) => n[0])
        .join("")
        .slice(0, 2)
        .toUpperCase()
    : member.user.email[0].toUpperCase();

  return (
    <Link
      href={`/gconsole/members/${member.id}`}
      className="hover:bg-muted/50 flex items-center gap-4 rounded-lg border p-4 transition-colors"
    >
      <Avatar className="h-10 w-10">
        <AvatarImage
          src={member.user.avatar_url ?? undefined}
          alt={member.user.display_name}
        />
        <AvatarFallback>{initials}</AvatarFallback>
      </Avatar>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <p className="truncate font-medium">
            {member.user.display_name || member.user.username}
          </p>
          <Badge variant={statusBadgeVariant(member.status)}>
            {member.status}
          </Badge>
          {member.is_owner && <Badge variant="outline">Owner</Badge>}
        </div>
        <p className="text-muted-foreground text-sm">
          {member.user.email} &middot; {member.account_name}
          {member.account_slug ? ` (${member.account_slug})` : ""} &middot;{" "}
          {member.role_name}
        </p>
      </div>
      <div className="text-muted-foreground hidden text-sm sm:block">
        {member.account_type}
      </div>
    </Link>
  );
}
