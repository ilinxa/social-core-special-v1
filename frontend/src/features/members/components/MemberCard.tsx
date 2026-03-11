"use client";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { StatusBadge } from "@/components/common/StatusBadge";
import { Badge } from "@/components/ui/badge";
import { MEMBER_STATUS_CONFIG } from "@/features/members/constants/member-statuses";
import type { MemberListItem } from "@/types/members";

interface MemberCardProps {
  member: MemberListItem;
  onClick?: () => void;
}

function getInitials(name: string): string {
  return name
    .split(" ")
    .map((n) => n[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);
}

export function MemberCard({ member, onClick }: MemberCardProps) {
  const { user, role_name, is_owner, status, joined_at } = member;

  return (
    <button
      type="button"
      onClick={onClick}
      className="flex w-full items-center gap-3 rounded-lg border p-3 text-left transition-colors hover:bg-muted/50"
    >
      <Avatar>
        {user.avatar_url ? (
          <AvatarImage src={user.avatar_url} alt={user.display_name} />
        ) : null}
        <AvatarFallback>
          {getInitials(user.display_name || user.username)}
        </AvatarFallback>
      </Avatar>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-medium truncate">
            {user.display_name || user.username}
          </span>
          {is_owner && (
            <Badge variant="secondary" className="text-xs shrink-0">
              Owner
            </Badge>
          )}
        </div>
        <p className="text-sm text-muted-foreground truncate">{user.email}</p>
      </div>

      <div className="flex items-center gap-2 shrink-0">
        <Badge variant="outline" className="text-xs">
          {role_name}
        </Badge>
        <StatusBadge status={status} statusMap={MEMBER_STATUS_CONFIG} />
      </div>

      <span className="text-xs text-muted-foreground shrink-0 hidden sm:block">
        {new Date(joined_at).toLocaleDateString()}
      </span>
    </button>
  );
}
