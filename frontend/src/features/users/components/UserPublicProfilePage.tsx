"use client";

import { useParams, useRouter } from "next/navigation";
import { Calendar, Lock, MapPin, Pencil, Tag, User } from "lucide-react";

import { useQueryClient } from "@tanstack/react-query";

import { Can } from "@/components/common/Can";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { COUNTRY_NAMES } from "@/lib/country-data";
import { queryKeys } from "@/lib/query-keys";
import { ConnectButton } from "@/features/network/components/ConnectButton";
import { useUserByUsername } from "@/features/users/hooks/use-user-queries";
import type { UserPublicWithRelationship, UserLimited } from "@/types";

// =============================================================================
// HELPERS
// =============================================================================

function getInitials(displayName: string, username: string): string {
  if (displayName && displayName !== username) return displayName[0].toUpperCase();
  return username[0]?.toUpperCase() ?? "?";
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
  });
}

function formatLocation(country: string, city: string): string {
  const parts: string[] = [];
  if (city) parts.push(city);
  if (country) parts.push(COUNTRY_NAMES[country] ?? country);
  return parts.join(", ");
}

// =============================================================================
// DETAIL ROW
// =============================================================================

function DetailRow({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-center gap-3 py-2.5">
      <div className="bg-muted flex h-9 w-9 shrink-0 items-center justify-center rounded-lg">
        <Icon className="text-muted-foreground h-4 w-4" />
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-muted-foreground text-xs">{label}</p>
        <p className="truncate text-sm font-medium">{value || "\u2014"}</p>
      </div>
    </div>
  );
}

// =============================================================================
// LOADING SKELETON
// =============================================================================

export function UserPublicProfileSkeleton() {
  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <Card className="overflow-hidden">
        <Skeleton className="aspect-3/1 w-full rounded-none" />
        <CardContent className="relative pt-0">
          <div className="flex flex-col items-center gap-4 sm:flex-row sm:items-end sm:gap-6">
            <Skeleton className="-mt-12 h-24 w-24 rounded-full" />
            <div className="flex-1 space-y-2 pb-2 text-center sm:text-left">
              <Skeleton className="mx-auto h-7 w-40 sm:mx-0" />
              <Skeleton className="mx-auto h-5 w-28 sm:mx-0" />
              <Skeleton className="mx-auto h-4 w-48 sm:mx-0" />
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="space-y-3 pt-6">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="flex items-center gap-3">
              <Skeleton className="h-9 w-9 rounded-lg" />
              <div className="space-y-1.5">
                <Skeleton className="h-3 w-16" />
                <Skeleton className="h-4 w-32" />
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}

// =============================================================================
// USER PUBLIC PROFILE VIEW (read-only)
// =============================================================================

interface UserPublicProfileViewProps {
  user: UserPublicWithRelationship;
  onAction?: () => void;
}

function UserPublicProfileView({ user, onAction }: UserPublicProfileViewProps) {
  const router = useRouter();
  const { profile, _permissions: permissions } = user;
  const relationship = user._relationship;

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      {/* Page header with connect + edit buttons */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold tracking-tight">Profile</h1>
        <div className="flex gap-2">
          <Can allowed={!permissions.is_own_profile}>
            <ConnectButton
              targetUserId={user.id}
              targetUsername={user.username}
              connectionStatus={relationship?.connection_status ?? null}
              connectionId={relationship?.connection_id ?? null}
              activeConnectionTransaction={relationship?.active_connection_transaction ?? null}
              onAction={onAction}
              size="sm"
            />
          </Can>
          <Can allowed={permissions.can_edit_profile}>
            <Button onClick={() => router.push("/profile/edit")} size="sm">
              <Pencil className="mr-2 h-3.5 w-3.5" />
              Edit Profile
            </Button>
          </Can>
        </div>
      </div>

      {/* Identity card with cover image */}
      <Card className="overflow-hidden">
        {/* Cover image */}
        {profile?.cover_image_url ? (
          <img
            src={profile.cover_image_url}
            alt="Cover"
            className="aspect-3/1 w-full object-cover"
          />
        ) : (
          <div className="bg-muted aspect-3/1 w-full" />
        )}

        <CardContent className="relative pt-0">
          <div className="flex flex-col items-center gap-4 sm:flex-row sm:items-end sm:gap-6">
            {/* Avatar — overlaps cover */}
            <div className="ring-background -mt-12 rounded-full ring-4">
              <Avatar className="h-24 w-24">
                <AvatarImage
                  src={profile?.avatar_url ?? undefined}
                  alt={profile?.display_name ?? user.username}
                />
                <AvatarFallback className="bg-primary/10 text-primary text-2xl font-semibold">
                  {getInitials(profile?.display_name ?? "", user.username)}
                </AvatarFallback>
              </Avatar>
            </div>

            {/* Name & meta */}
            <div className="flex flex-1 flex-col pb-2 text-center sm:text-left">
              <h2 className="text-xl font-semibold">
                {profile?.display_name || user.username}
              </h2>
              <p className="text-muted-foreground mt-0.5 text-sm font-medium">
                @{user.username}
              </p>

              {/* Badges */}
              <div className="mt-2 flex flex-wrap items-center gap-1.5">
                {user.is_verified ? (
                  <Badge
                    variant="default"
                    className="bg-success text-success-foreground text-xs hover:bg-success/90"
                  >
                    Verified
                  </Badge>
                ) : (
                  <Badge variant="secondary" className="text-xs">
                    Unverified
                  </Badge>
                )}
                <span className="text-muted-foreground flex items-center gap-1 text-xs">
                  <Calendar className="h-3 w-3" />
                  Member since {formatDate(user.date_joined)}
                </span>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Bio card */}
      {profile?.bio && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">About</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm leading-relaxed whitespace-pre-line">{profile.bio}</p>
          </CardContent>
        </Card>
      )}

      {/* Info card */}
      {profile && (profile.first_name || profile.last_name || profile.country || profile.city) && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Information</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="divide-y">
              {(profile.first_name || profile.last_name) && (
                <DetailRow
                  icon={User}
                  label="Name"
                  value={[profile.first_name, profile.last_name].filter(Boolean).join(" ")}
                />
              )}
              {(profile.country || profile.city) && (
                <DetailRow
                  icon={MapPin}
                  label="Location"
                  value={formatLocation(profile.country, profile.city)}
                />
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Tags card */}
      {profile?.tags && profile.tags.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Tags</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {profile.tags.map((tag) => (
                <Badge key={tag} variant="secondary">
                  <Tag className="mr-1 h-3 w-3" />
                  {tag}
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// =============================================================================
// LIMITED (PRIVATE) PROFILE VIEW
// =============================================================================

function UserLimitedProfileView({
  user,
  onAction,
}: {
  user: UserLimited;
  onAction?: () => void;
}) {
  const { profile } = user;
  const relationship = user._relationship;
  const isOwnProfile = user._permissions?.is_own_profile ?? false;

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold tracking-tight">Profile</h1>
        <Can allowed={!isOwnProfile}>
          <ConnectButton
            targetUserId={user.id}
            targetUsername={user.username}
            connectionStatus={relationship?.connection_status ?? null}
            connectionId={relationship?.connection_id ?? null}
            activeConnectionTransaction={relationship?.active_connection_transaction ?? null}
            onAction={onAction}
            size="sm"
          />
        </Can>
      </div>

      {/* Identity card */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col items-center gap-4 sm:flex-row sm:items-start sm:gap-6">
            <div className="ring-primary/20 relative rounded-full ring-4 ring-offset-2">
              <Avatar className="h-24 w-24">
                <AvatarImage
                  src={profile.avatar_url ?? undefined}
                  alt={profile.display_name}
                />
                <AvatarFallback className="bg-primary/10 text-primary text-2xl font-semibold">
                  {getInitials(profile.display_name, user.username)}
                </AvatarFallback>
              </Avatar>
            </div>

            <div className="flex flex-1 flex-col text-center sm:text-left">
              <h2 className="text-xl font-semibold">{profile.display_name}</h2>
              <p className="text-muted-foreground mt-0.5 text-sm font-medium">
                @{user.username}
              </p>
              <div className="mt-2 flex flex-wrap items-center gap-1.5">
                {user.is_verified && (
                  <Badge
                    variant="default"
                    className="bg-success text-success-foreground text-xs hover:bg-success/90"
                  >
                    Verified
                  </Badge>
                )}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Private profile notice */}
      <Card className="border-muted">
        <CardContent className="flex items-center gap-3 py-6">
          <div className="bg-muted flex h-10 w-10 shrink-0 items-center justify-center rounded-full">
            <Lock className="text-muted-foreground h-5 w-5" />
          </div>
          <div>
            <p className="font-medium">This profile is private</p>
            <p className="text-muted-foreground text-sm">
              This user has chosen to keep their profile information private.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// =============================================================================
// TYPE GUARD
// =============================================================================

function isLimitedProfile(
  data: UserPublicWithRelationship | UserLimited,
): data is UserLimited {
  return "is_limited" in data && data.is_limited === true;
}

// =============================================================================
// PAGE COMPONENT
// =============================================================================

export function UserPublicProfilePage() {
  const { username } = useParams<{ username: string }>();
  const queryClient = useQueryClient();
  const { data: user, isLoading, error } = useUserByUsername(username);

  function invalidate() {
    queryClient.invalidateQueries({
      queryKey: queryKeys.users.byUsername(username),
    });
  }

  if (isLoading) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-8">
        <UserPublicProfileSkeleton />
      </div>
    );
  }

  if (error || !user) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-16 text-center">
        <h2 className="text-xl font-semibold">User not found</h2>
        <p className="text-muted-foreground mt-2 text-sm">
          This user profile may not exist or is not accessible.
        </p>
      </div>
    );
  }

  if (isLimitedProfile(user)) {
    return (
      <div className="px-4 py-8">
        <UserLimitedProfileView user={user} onAction={invalidate} />
      </div>
    );
  }

  return (
    <div className="px-4 py-8">
      <UserPublicProfileView user={user} onAction={invalidate} />
    </div>
  );
}
