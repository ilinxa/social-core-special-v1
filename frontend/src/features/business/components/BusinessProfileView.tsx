"use client";

import {
  Briefcase,
  Building2,
  Calendar,
  ExternalLink,
  Globe,
  Mail,
  MapPin,
  Phone,
  Tag,
  Users,
} from "lucide-react";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { COUNTRY_NAMES } from "@/lib/country-data";
import type { BusinessAccountWithPerms } from "@/types/organization";

// =============================================================================
// HELPERS
// =============================================================================

function getInitial(name: string): string {
  return name[0]?.toUpperCase() ?? "B";
}

function findSizeLabel(size: string): string {
  const map: Record<string, string> = {
    "1": "1 employee",
    "2-10": "2-10 employees",
    "11-50": "11-50 employees",
    "51-200": "51-200 employees",
    "201-500": "201-500 employees",
    "500+": "500+ employees",
  };
  return map[size] ?? size;
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

export function BusinessProfileSkeleton() {
  return (
    <div className="space-y-6">
      {/* Hero */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col items-center gap-4 sm:flex-row sm:items-start sm:gap-6">
            <Skeleton className="h-20 w-20 rounded-lg" />
            <div className="flex-1 space-y-2 text-center sm:text-left">
              <Skeleton className="mx-auto h-7 w-48 sm:mx-0" />
              <Skeleton className="mx-auto h-5 w-64 sm:mx-0" />
              <Skeleton className="mx-auto h-4 w-32 sm:mx-0" />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Details */}
      <Card>
        <CardContent className="space-y-3 pt-6">
          {Array.from({ length: 4 }).map((_, i) => (
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
// BUSINESS PROFILE VIEW
// =============================================================================

interface BusinessProfileViewProps {
  business: BusinessAccountWithPerms;
}

export function BusinessProfileView({ business }: BusinessProfileViewProps) {
  const { profile } = business;

  return (
    <div className="space-y-6">
      {/* Cover image */}
      {profile.cover_image && (
        <div className="aspect-[3/1] w-full overflow-hidden rounded-lg">
          <img
            src={profile.cover_image}
            alt={`${profile.display_name} cover`}
            className="h-full w-full object-cover"
          />
        </div>
      )}

      {/* Identity card */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col items-center gap-4 sm:flex-row sm:items-start sm:gap-6">
            {/* Logo */}
            <Avatar className="h-20 w-20 rounded-lg">
              <AvatarImage src={profile.logo ?? undefined} alt={profile.display_name} />
              <AvatarFallback className="bg-primary/10 text-primary rounded-lg text-2xl font-semibold">
                {getInitial(profile.display_name || business.legal_name)}
              </AvatarFallback>
            </Avatar>

            {/* Info */}
            <div className="flex flex-1 flex-col text-center sm:text-left">
              <h2 className="text-xl font-semibold">
                {profile.display_name || business.legal_name}
              </h2>
              {profile.tagline && (
                <p className="text-muted-foreground mt-0.5 text-sm">{profile.tagline}</p>
              )}

              {/* Badges */}
              <div className="mt-2 flex flex-wrap items-center gap-1.5">
                <Badge variant="outline" className="capitalize text-xs">
                  {business.status_display}
                </Badge>
                {business.verification_status === "verified" && (
                  <Badge variant="default" className="bg-green-100 text-green-800 border-green-300 text-xs">
                    Verified
                  </Badge>
                )}
                {!profile.is_public && (
                  <Badge variant="secondary" className="text-xs">Private</Badge>
                )}
              </div>
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

      {/* Business details */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Details</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="divide-y">
            <DetailRow icon={Building2} label="Industry" value={profile.industry} />
            <DetailRow icon={Briefcase} label="Business type" value={business.business_type_display} />
            <DetailRow icon={Users} label="Company size" value={findSizeLabel(profile.company_size)} />
            <DetailRow icon={MapPin} label="Location" value={formatLocation(business.country, business.city)} />
            {profile.founded_year && (
              <DetailRow icon={Calendar} label="Founded" value={String(profile.founded_year)} />
            )}
          </div>
        </CardContent>
      </Card>

      {/* Tags */}
      {profile.tags.length > 0 && (
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

      {/* Contact */}
      {(profile.website || profile.contact_email || profile.contact_phone) && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Contact</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="divide-y">
              {profile.website && (
                <DetailRow icon={Globe} label="Website" value={profile.website} href={profile.website} />
              )}
              {profile.contact_email && (
                <DetailRow icon={Mail} label="Email" value={profile.contact_email} href={`mailto:${profile.contact_email}`} />
              )}
              {profile.contact_phone && (
                <DetailRow icon={Phone} label="Phone" value={profile.contact_phone} />
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
