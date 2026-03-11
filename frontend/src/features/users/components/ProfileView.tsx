"use client";

import { useRouter } from "next/navigation";
import { Calendar, Globe, Languages, Mail, MapPin, Pencil, Phone, Tag, User } from "lucide-react";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { COUNTRY_NAMES } from "@/lib/country-data";
import { useProfile } from "@/features/users/hooks/use-user-queries";
import { useUser } from "@/stores/auth-store";

// =============================================================================
// HELPERS
// =============================================================================

function getInitials(displayName: string, email: string): string {
  if (displayName && displayName !== email) return displayName[0].toUpperCase();
  return email[0]?.toUpperCase() ?? "?";
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
  });
}

function findLanguageLabel(code: string): string {
  const map: Record<string, string> = {
    en: "English",
    es: "Spanish",
    fr: "French",
    de: "German",
    ar: "Arabic",
    zh: "Chinese",
    ja: "Japanese",
    ko: "Korean",
    pt: "Portuguese",
    ru: "Russian",
  };
  return map[code] ?? code;
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

function ProfileSkeleton() {
  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div className="flex items-center justify-between">
        <Skeleton className="h-8 w-32" />
        <Skeleton className="h-9 w-28" />
      </div>

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
          {Array.from({ length: 5 }).map((_, i) => (
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
// PROFILE VIEW
// =============================================================================

export function ProfileView() {
  const user = useUser();
  const { data: profile, isLoading } = useProfile();
  const router = useRouter();

  if (isLoading || !user || !profile) {
    return <ProfileSkeleton />;
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold tracking-tight">Profile</h1>
        <Button onClick={() => router.push("/profile/edit")} size="sm">
          <Pencil className="mr-2 h-3.5 w-3.5" />
          Edit Profile
        </Button>
      </div>

      {/* Identity card with cover image */}
      <Card className="overflow-hidden">
        {/* Cover image */}
        {profile.cover_image_url ? (
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
                <AvatarImage src={profile.avatar_url ?? undefined} alt={profile.display_name} />
                <AvatarFallback className="bg-primary/10 text-primary text-2xl font-semibold">
                  {getInitials(profile.display_name, user.email)}
                </AvatarFallback>
              </Avatar>
            </div>

            {/* Name & meta */}
            <div className="flex flex-1 flex-col pb-2 text-center sm:text-left">
              <h2 className="text-xl font-semibold">{profile.display_name}</h2>
              <p className="text-muted-foreground mt-0.5 flex items-center gap-1 text-sm font-medium">
                @{user.username}
              </p>
              <p className="text-muted-foreground mt-0.5 flex items-center gap-1 text-sm font-medium">
                <Mail className="h-3.5 w-3.5" />
                {user.email}
              </p>

              {/* Badges */}
              <div className="mt-2 flex flex-wrap items-center gap-1.5">
                {user.is_verified ? (
                  <Badge variant="default" className="bg-success text-success-foreground text-xs hover:bg-success/90">
                    Verified
                  </Badge>
                ) : (
                  <Badge variant="secondary" className="text-xs">
                    Unverified
                  </Badge>
                )}
                {user.is_complete ? (
                  <Badge variant="default" className="bg-success text-success-foreground text-xs hover:bg-success/90">
                    Complete
                  </Badge>
                ) : (
                  <Badge variant="secondary" className="text-xs">
                    Incomplete
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
      {profile.bio && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">About</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm leading-relaxed whitespace-pre-line">{profile.bio}</p>
          </CardContent>
        </Card>
      )}

      {/* Details card */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Personal Information</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="divide-y">
            <DetailRow icon={User} label="First name" value={profile.first_name} />
            <DetailRow icon={User} label="Last name" value={profile.last_name} />
          </div>

          <Separator className="my-1" />

          <div className="divide-y">
            <DetailRow icon={Phone} label="Phone" value={profile.phone} />
            <DetailRow icon={MapPin} label="Location" value={formatLocation(profile.country, profile.city)} />
            <DetailRow icon={Globe} label="Timezone" value={profile.timezone.replace(/_/g, " ")} />
            <DetailRow icon={Languages} label="Language" value={findLanguageLabel(profile.language)} />
          </div>
        </CardContent>
      </Card>

      {/* Tags card */}
      {profile.tags && profile.tags.length > 0 && (
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
