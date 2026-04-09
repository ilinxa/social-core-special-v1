"use client";

import { useState } from "react";
import Link from "next/link";
import { Search, User } from "lucide-react";

import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { useGovernanceApprovedCreators } from "@/features/governance/hooks/use-governance-queries";
import type { ApprovedCreatorItem } from "@/types";

export function GovernanceApprovedCreatorsPage() {
  const [search, setSearch] = useState("");
  const [ordering, setOrdering] = useState("newest");
  const [page, setPage] = useState(1);

  const params: Record<string, unknown> = {
    page,
    page_size: 20,
    ordering,
  };
  if (search.trim()) {
    params.search = search.trim();
  }

  const { data, isLoading } = useGovernanceApprovedCreators(params);

  function handleSearchChange(value: string) {
    setSearch(value);
    setPage(1);
  }

  function handleOrderingChange(value: string) {
    setOrdering(value);
    setPage(1);
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">Approved Business Creators</h1>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <Search className="text-muted-foreground absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2" />
          <Input
            placeholder="Search by name, email, or username..."
            value={search}
            onChange={(e) => handleSearchChange(e.target.value)}
            className="pl-9"
          />
        </div>
        <Select value={ordering} onValueChange={handleOrderingChange}>
          <SelectTrigger className="w-[160px]">
            <SelectValue placeholder="Sort by" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="newest">Newest</SelectItem>
            <SelectItem value="name">Name</SelectItem>
            <SelectItem value="email">Email</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-16 w-full rounded-lg" />
          ))}
        </div>
      ) : !data?.results.length ? (
        <div className="text-muted-foreground py-12 text-center">
          {search ? "No users match your search." : "No users have been approved yet."}
        </div>
      ) : (
        <>
          <p className="text-muted-foreground text-sm">
            {data.count} approved {data.count === 1 ? "creator" : "creators"}
          </p>
          <div className="space-y-2">
            {data.results.map((creator: ApprovedCreatorItem) => (
              <CreatorCard key={creator.id} creator={creator} />
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

function CreatorCard({ creator }: { creator: ApprovedCreatorItem }) {
  const initials = creator.display_name
    .split(" ")
    .map((n) => n[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  return (
    <Link
      href={`/users/${creator.username}`}
      className="hover:bg-muted/50 flex items-center gap-4 rounded-lg border p-4 transition-colors"
    >
      <Avatar>
        {creator.avatar_url ? (
          <AvatarImage src={creator.avatar_url} alt={creator.display_name} />
        ) : null}
        <AvatarFallback>
          {initials || <User className="h-4 w-4" />}
        </AvatarFallback>
      </Avatar>
      <div className="min-w-0 flex-1">
        <p className="truncate font-medium">{creator.display_name}</p>
        <p className="text-muted-foreground truncate text-sm">{creator.email}</p>
      </div>
      <div className="text-muted-foreground hidden text-sm sm:block">
        Joined {new Date(creator.date_joined).toLocaleDateString()}
      </div>
    </Link>
  );
}
