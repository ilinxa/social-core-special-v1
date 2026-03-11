"use client";

import { ExternalLink, Globe, Mail, MapPin, Phone } from "lucide-react";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { PlatformAccountWithPerms } from "@/types/organization";

// =============================================================================
// DETAIL ROW
// =============================================================================

function DetailRow({
  icon: Icon,
  label,
  value,
  href,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string;
  href?: string;
}) {
  return (
    <div className="flex items-center gap-3 py-2.5">
      <div className="bg-muted flex h-9 w-9 shrink-0 items-center justify-center rounded-lg">
        <Icon className="text-muted-foreground h-4 w-4" />
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-muted-foreground text-xs">{label}</p>
        {href && value ? (
          <a
            href={href}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 truncate text-sm font-medium text-primary hover:underline"
          >
            {value}
            <ExternalLink className="h-3 w-3 shrink-0" />
          </a>
        ) : (
          <p className="truncate text-sm font-medium">{value || "\u2014"}</p>
        )}
      </div>
    </div>
  );
}

// =============================================================================
// COLOR SWATCH
// =============================================================================

function ColorSwatch({ label, color }: { label: string; color: string }) {
  return (
    <div className="flex items-center gap-3">
      <div
        className="h-8 w-8 rounded-md border"
        style={{ backgroundColor: color }}
        aria-label={`${label}: ${color}`}
      />
      <div>
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className="font-mono text-sm">{color}</p>
      </div>
    </div>
  );
}

// =============================================================================
// SOCIAL LINKS DISPLAY
// =============================================================================

function SocialLinksDisplay({ links }: { links: Record<string, string> }) {
  const entries = Object.entries(links).filter(([, url]) => url);
  if (entries.length === 0) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Social Links</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex flex-wrap gap-2">
          {entries.map(([platform, url]) => (
            <a
              key={platform}
              href={url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-sm font-medium capitalize transition-colors hover:bg-muted"
            >
              {platform}
              <ExternalLink className="h-3 w-3" />
            </a>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

// =============================================================================
// LOADING SKELETON
// =============================================================================

export function PlatformProfileSkeleton() {
  return (
    <div className="space-y-6">
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col items-center gap-4 sm:flex-row sm:items-start sm:gap-6">
            <Skeleton className="h-20 w-20 rounded-lg" />
            <div className="flex-1 space-y-2 text-center sm:text-left">
              <Skeleton className="mx-auto h-7 w-48 sm:mx-0" />
              <Skeleton className="mx-auto h-5 w-64 sm:mx-0" />
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
// PLATFORM PROFILE VIEW
// =============================================================================

interface PlatformProfileViewProps {
  account: PlatformAccountWithPerms;
}

export function PlatformProfileView({ account }: PlatformProfileViewProps) {
  const { profile } = account;

  return (
    <div className="space-y-6">
      {/* Identity card */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col items-center gap-4 sm:flex-row sm:items-start sm:gap-6">
            {/* Logo */}
            <Avatar className="h-20 w-20 rounded-lg">
              <AvatarImage src={profile.logo ?? undefined} alt={profile.name} />
              <AvatarFallback className="bg-primary/10 text-primary rounded-lg text-2xl font-semibold">
                {profile.name[0]?.toUpperCase() ?? "P"}
              </AvatarFallback>
            </Avatar>

            {/* Info */}
            <div className="flex flex-1 flex-col text-center sm:text-left">
              <h2 className="text-xl font-semibold">{profile.name}</h2>
              {profile.tagline && (
                <p className="text-muted-foreground mt-0.5 text-sm">{profile.tagline}</p>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Description */}
      {profile.description && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">About</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm leading-relaxed whitespace-pre-line">{profile.description}</p>
          </CardContent>
        </Card>
      )}

      {/* Branding */}
      {(profile.primary_color || profile.secondary_color) && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Branding</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-6">
              {profile.primary_color && (
                <ColorSwatch label="Primary color" color={profile.primary_color} />
              )}
              {profile.secondary_color && (
                <ColorSwatch label="Secondary color" color={profile.secondary_color} />
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Contact */}
      {(profile.contact_email || profile.contact_phone || profile.address) && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Contact</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="divide-y">
              {profile.contact_email && (
                <DetailRow icon={Mail} label="Email" value={profile.contact_email} href={`mailto:${profile.contact_email}`} />
              )}
              {profile.contact_phone && (
                <DetailRow icon={Phone} label="Phone" value={profile.contact_phone} />
              )}
              {profile.address && (
                <DetailRow icon={MapPin} label="Address" value={profile.address} />
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Social links */}
      <SocialLinksDisplay links={profile.social_links} />
    </div>
  );
}
