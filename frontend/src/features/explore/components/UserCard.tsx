"use client";

import { BadgeCheck, MapPin } from "lucide-react";
import Link from "next/link";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import type { ExploreUser } from "@/types/explore";

interface UserCardProps {
  user: ExploreUser;
}

export function UserCard({ user }: UserCardProps) {
  const profile = user.profile ?? {
    first_name: "",
    last_name: "",
    bio: "",
    avatar_url: null,
    country: "",
    city: "",
    tags: [],
  };
  const location = [profile.city, profile.country].filter(Boolean).join(", ");
  const initials = [profile.first_name, profile.last_name]
    .filter(Boolean)
    .map((n) => n.charAt(0))
    .join("")
    .toUpperCase() || user.username.charAt(0).toUpperCase();

  return (
    <Card className="transition-colors hover:bg-accent/50">
      <Link href={`/users/${user.username}`} className="block">
        <CardContent className="flex gap-4 p-4">
          {/* Avatar */}
          <Avatar className="h-12 w-12 shrink-0">
            <AvatarImage src={profile.avatar_url ?? undefined} alt={user.display_name} />
            <AvatarFallback>{initials}</AvatarFallback>
          </Avatar>

          {/* Info */}
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-1.5">
              <h3 className="truncate font-medium">{user.display_name}</h3>
              {user.is_verified && (
                <BadgeCheck className="h-4 w-4 shrink-0 text-blue-500" aria-label="Verified" />
              )}
            </div>

            <p className="text-sm text-muted-foreground">@{user.username}</p>

            {profile.bio && (
              <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">
                {profile.bio}
              </p>
            )}

            <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
              {location && (
                <span className="flex items-center gap-1">
                  <MapPin className="h-3 w-3" />
                  {location}
                </span>
              )}
            </div>

            {profile.tags.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1">
                {profile.tags.slice(0, 3).map((tag) => (
                  <Badge key={tag} variant="secondary" className="text-xs">
                    {tag}
                  </Badge>
                ))}
                {profile.tags.length > 3 && (
                  <Badge variant="outline" className="text-xs">
                    +{profile.tags.length - 3}
                  </Badge>
                )}
              </div>
            )}
          </div>
        </CardContent>
      </Link>
    </Card>
  );
}
