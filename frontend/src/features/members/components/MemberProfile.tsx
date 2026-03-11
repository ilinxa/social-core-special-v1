"use client";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/common/StatusBadge";
import { MEMBER_STATUS_CONFIG } from "@/features/members/constants/member-statuses";
import type { MemberDetail } from "@/types/members";

interface MemberProfileProps {
  member: MemberDetail;
}

function getInitials(name: string): string {
  return name
    .split(" ")
    .map((n) => n[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);
}

export function MemberProfile({ member }: MemberProfileProps) {
  const { user, role, is_owner, status, joined_at, status_changed_at, status_reason } = member;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Member Info</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* User info */}
        <div className="flex items-center gap-4">
          <Avatar size="lg">
            {user.avatar_url ? (
              <AvatarImage src={user.avatar_url} alt={user.display_name} />
            ) : null}
            <AvatarFallback>
              {getInitials(user.display_name || user.username)}
            </AvatarFallback>
          </Avatar>
          <div>
            <h3 className="font-semibold text-lg">
              {user.display_name || user.username}
            </h3>
            <p className="text-sm text-muted-foreground">{user.email}</p>
            <p className="text-sm text-muted-foreground">@{user.username}</p>
          </div>
        </div>

        {/* Membership details */}
        <div className="grid gap-3 text-sm">
          <div className="flex justify-between">
            <span className="text-muted-foreground">Role</span>
            <div className="flex items-center gap-2">
              <Badge variant="outline">{role.name}</Badge>
              <span className="text-xs text-muted-foreground">
                (Level {role.level})
              </span>
            </div>
          </div>

          <div className="flex justify-between">
            <span className="text-muted-foreground">Status</span>
            <StatusBadge status={status} statusMap={MEMBER_STATUS_CONFIG} />
          </div>

          {is_owner && (
            <div className="flex justify-between">
              <span className="text-muted-foreground">Ownership</span>
              <Badge variant="secondary">Owner</Badge>
            </div>
          )}

          <div className="flex justify-between">
            <span className="text-muted-foreground">Joined</span>
            <span>{new Date(joined_at).toLocaleDateString()}</span>
          </div>

          {status_changed_at && (
            <div className="flex justify-between">
              <span className="text-muted-foreground">Status changed</span>
              <span>{new Date(status_changed_at).toLocaleDateString()}</span>
            </div>
          )}

          {status_reason && (
            <div className="flex justify-between">
              <span className="text-muted-foreground">Reason</span>
              <span className="text-right max-w-[200px]">{status_reason}</span>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
