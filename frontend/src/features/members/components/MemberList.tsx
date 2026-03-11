"use client";

import { useState } from "react";
import { Input } from "@/components/ui/input";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Search, ChevronLeft, ChevronRight } from "lucide-react";
import { MemberCard } from "./MemberCard";
import {
  MEMBER_STATUS_TABS,
  MEMBER_ORDERING_OPTIONS,
} from "@/features/members/constants/member-statuses";
import type { MemberListItem, MemberListParams, RoleListItem } from "@/types/members";
import type { PaginatedResponse } from "@/types";
import type { MembershipStatus } from "@/types/rbac";

interface MemberListProps {
  data?: PaginatedResponse<MemberListItem>;
  roles?: RoleListItem[];
  params: MemberListParams;
  onParamsChange: (params: MemberListParams) => void;
  onMemberClick: (memberId: string) => void;
  isLoading?: boolean;
}

export function MemberList({
  data,
  roles,
  params,
  onParamsChange,
  onMemberClick,
  isLoading,
}: MemberListProps) {
  const [searchInput, setSearchInput] = useState(params.search ?? "");

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    onParamsChange({ ...params, search: searchInput || undefined, page: 1 });
  }

  function handleStatusChange(status: string) {
    const newStatus = status === "all" ? undefined : (status as MembershipStatus);
    onParamsChange({ ...params, status: newStatus, page: 1 });
  }

  function handleRoleFilter(roleId: string) {
    onParamsChange({
      ...params,
      role_id: roleId === "all" ? undefined : roleId,
      page: 1,
    });
  }

  function handleOrderingChange(ordering: string) {
    onParamsChange({ ...params, ordering, page: 1 });
  }

  const currentPage = params.page ?? 1;
  const pageSize = params.page_size ?? 20;
  const totalPages = data ? Math.ceil(data.count / pageSize) : 0;

  return (
    <div className="space-y-4">
      {/* Filters row */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <form onSubmit={handleSearch} className="flex gap-2 flex-1 max-w-sm">
          <div className="relative flex-1">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search members..."
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              className="pl-9"
            />
          </div>
        </form>

        <div className="flex gap-2">
          {roles && roles.length > 0 && (
            <Select
              value={params.role_id ?? "all"}
              onValueChange={handleRoleFilter}
            >
              <SelectTrigger className="w-[140px]">
                <SelectValue placeholder="All roles" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All roles</SelectItem>
                {roles.map((role) => (
                  <SelectItem key={role.id} value={role.id}>
                    {role.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
          <Select
            value={params.ordering ?? "name"}
            onValueChange={handleOrderingChange}
          >
            <SelectTrigger className="w-[150px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {MEMBER_ORDERING_OPTIONS.map((opt) => (
                <SelectItem key={opt.value} value={opt.value}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Status tabs */}
      <Tabs
        value={params.status ?? "all"}
        onValueChange={handleStatusChange}
      >
        <TabsList>
          <TabsTrigger value="all">All</TabsTrigger>
          {MEMBER_STATUS_TABS.map((tab) => (
            <TabsTrigger key={tab.value} value={tab.value}>
              {tab.label}
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>

      {/* Member list */}
      <div className="space-y-1">
        {isLoading ? (
          Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="flex items-center gap-3 p-3">
              <Skeleton className="h-8 w-8 rounded-full" />
              <div className="flex-1 space-y-1">
                <Skeleton className="h-4 w-32" />
                <Skeleton className="h-3 w-48" />
              </div>
            </div>
          ))
        ) : data?.results.length === 0 ? (
          <p className="py-8 text-center text-muted-foreground">
            No members found.
          </p>
        ) : (
          data?.results.map((member) => (
            <MemberCard
              key={member.id}
              member={member}
              onClick={() => onMemberClick(member.id)}
            />
          ))
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            {data?.count} total members
          </p>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={currentPage <= 1}
              onClick={() =>
                onParamsChange({ ...params, page: currentPage - 1 })
              }
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <span className="text-sm">
              Page {currentPage} of {totalPages}
            </span>
            <Button
              variant="outline"
              size="sm"
              disabled={currentPage >= totalPages}
              onClick={() =>
                onParamsChange({ ...params, page: currentPage + 1 })
              }
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
