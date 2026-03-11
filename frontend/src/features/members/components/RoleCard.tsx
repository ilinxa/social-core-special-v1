"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Users, Shield } from "lucide-react";
import type { RoleListItem } from "@/types/members";

interface RoleCardProps {
  role: RoleListItem;
  onClick?: () => void;
}

export function RoleCard({ role, onClick }: RoleCardProps) {
  return (
    <Card
      className="cursor-pointer transition-colors hover:bg-muted/50"
      onClick={onClick}
    >
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base flex items-center gap-2">
            <Shield className="h-4 w-4 text-muted-foreground" />
            {role.name}
          </CardTitle>
          {role.is_system_role && (
            <Badge variant="secondary" className="text-xs">
              System
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground">Level {role.level}</span>
          <span className="flex items-center gap-1 text-muted-foreground">
            <Users className="h-3.5 w-3.5" />
            {role.member_count} {role.member_count === 1 ? "member" : "members"}
          </span>
        </div>
        {role.description && (
          <p className="mt-2 text-sm text-muted-foreground line-clamp-2">
            {role.description}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
