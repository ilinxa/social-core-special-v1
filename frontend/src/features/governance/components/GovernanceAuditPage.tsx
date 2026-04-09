"use client";

import { useState } from "react";
import { Clock, Filter, Shield } from "lucide-react";

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
import { useGovernanceAuditLogs } from "@/features/governance/hooks/use-governance-queries";
import type { GovernanceAuditLog } from "@/types/governance";

const OUTCOME_OPTIONS = [
  { value: "all", label: "All Outcomes" },
  { value: "SUCCESS", label: "Success" },
  { value: "FAILURE", label: "Failure" },
  { value: "DENIED", label: "Denied" },
];

function outcomeBadgeVariant(
  outcome: string,
): "default" | "secondary" | "destructive" | "outline" {
  switch (outcome) {
    case "SUCCESS":
      return "default";
    case "FAILURE":
      return "destructive";
    case "DENIED":
      return "outline";
    default:
      return "secondary";
  }
}

function actorTypeBadgeVariant(
  actorType: string,
): "default" | "secondary" | "destructive" | "outline" {
  switch (actorType) {
    case "ADMIN":
      return "outline";
    case "SYSTEM":
      return "secondary";
    default:
      return "default";
  }
}

export function GovernanceAuditPage() {
  const [action, setAction] = useState("");
  const [outcome, setOutcome] = useState("all");
  const [resourceType, setResourceType] = useState("");
  const [page, setPage] = useState(1);

  const params: Record<string, unknown> = { page, page_size: 25 };
  if (action.trim()) params.action = action.trim();
  if (outcome !== "all") params.outcome = outcome;
  if (resourceType.trim()) params.resource_type = resourceType.trim();

  const { data, isLoading } = useGovernanceAuditLogs(params);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">Audit Log</h1>

      {/* Filter bar */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <Filter className="text-muted-foreground absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2" />
          <Input
            placeholder="Filter by action..."
            value={action}
            onChange={(e) => {
              setAction(e.target.value);
              setPage(1);
            }}
            className="pl-9"
          />
        </div>
        <Input
          placeholder="Resource type..."
          value={resourceType}
          onChange={(e) => {
            setResourceType(e.target.value);
            setPage(1);
          }}
          className="w-[180px]"
        />
        <Select
          value={outcome}
          onValueChange={(v) => {
            setOutcome(v);
            setPage(1);
          }}
        >
          <SelectTrigger className="w-[160px]">
            <SelectValue placeholder="Outcome" />
          </SelectTrigger>
          <SelectContent>
            {OUTCOME_OPTIONS.map((opt) => (
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
          {Array.from({ length: 8 }).map((_, i) => (
            <Skeleton key={i} className="h-16 w-full rounded-lg" />
          ))}
        </div>
      ) : !data?.results.length ? (
        <div className="text-muted-foreground py-12 text-center">
          No audit log entries found.
        </div>
      ) : (
        <>
          <p className="text-muted-foreground text-sm">
            {data.count} {data.count === 1 ? "entry" : "entries"}
          </p>
          <div className="space-y-2">
            {data.results.map((entry) => (
              <AuditLogEntry key={entry.id} entry={entry} />
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

function AuditLogEntry({ entry }: { entry: GovernanceAuditLog }) {
  const [expanded, setExpanded] = useState(false);
  const timestamp = new Date(entry.timestamp).toLocaleString();

  return (
    <div className="rounded-lg border p-4">
      <button
        type="button"
        className="flex w-full items-start gap-4 text-left"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="bg-muted flex h-9 w-9 shrink-0 items-center justify-center rounded-lg">
          <Shield className="text-muted-foreground h-4 w-4" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-medium">{entry.action}</span>
            <Badge variant={outcomeBadgeVariant(entry.outcome)}>
              {entry.outcome}
            </Badge>
            <Badge variant={actorTypeBadgeVariant(entry.actor_type)}>
              {entry.actor_type}
            </Badge>
          </div>
          <p className="text-muted-foreground mt-1 text-sm">
            {entry.actor_email} &middot; {entry.resource_type}
            {entry.resource_repr ? `: ${entry.resource_repr}` : ""}
          </p>
        </div>
        <div className="text-muted-foreground flex shrink-0 items-center gap-1 text-xs">
          <Clock className="h-3 w-3" />
          <span>{timestamp}</span>
        </div>
      </button>

      {expanded && (entry.details || entry.changes) && (
        <div className="mt-3 space-y-2 border-t pt-3">
          {entry.details && Object.keys(entry.details).length > 0 && (
            <div>
              <p className="text-xs font-medium uppercase tracking-wide">
                Details
              </p>
              <pre className="bg-muted mt-1 overflow-x-auto rounded p-2 text-xs">
                {JSON.stringify(entry.details, null, 2)}
              </pre>
            </div>
          )}
          {entry.changes && Object.keys(entry.changes).length > 0 && (
            <div>
              <p className="text-xs font-medium uppercase tracking-wide">
                Changes
              </p>
              <pre className="bg-muted mt-1 overflow-x-auto rounded p-2 text-xs">
                {JSON.stringify(entry.changes, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
