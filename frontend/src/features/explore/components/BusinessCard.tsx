"use client";

import { BadgeCheck, Globe, MapPin } from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import type { ExploreBusiness } from "@/types/explore";

interface BusinessCardProps {
  business: ExploreBusiness;
}

export function BusinessCard({ business }: BusinessCardProps) {
  const profile = business.profile ?? {
    display_name: business.legal_name,
    tagline: "",
    logo: null,
    industry: "",
    company_size: "",
    tags: [],
    website: "",
  };
  const location = [business.city, business.country].filter(Boolean).join(", ");

  return (
    <Card className="transition-colors hover:bg-accent/50">
      <Link href={`/business/${business.slug}`} className="block">
        <CardContent className="flex gap-4 p-4">
          {/* Logo */}
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-muted text-lg font-semibold text-muted-foreground">
            {profile.logo ? (
              <img
                src={profile.logo}
                alt={profile.display_name}
                className="h-12 w-12 rounded-lg object-cover"
              />
            ) : (
              profile.display_name.charAt(0).toUpperCase()
            )}
          </div>

          {/* Info */}
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-1.5">
              <h3 className="truncate font-medium">{profile.display_name}</h3>
              {business.is_verified && (
                <BadgeCheck className="h-4 w-4 shrink-0 text-blue-500" aria-label="Verified" />
              )}
            </div>

            {profile.tagline && (
              <p className="mt-0.5 truncate text-sm text-muted-foreground">
                {profile.tagline}
              </p>
            )}

            <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
              {profile.industry && <span>{profile.industry}</span>}
              {location && (
                <span className="flex items-center gap-1">
                  <MapPin className="h-3 w-3" />
                  {location}
                </span>
              )}
              {profile.website && (
                <span className="flex items-center gap-1">
                  <Globe className="h-3 w-3" />
                  Website
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
