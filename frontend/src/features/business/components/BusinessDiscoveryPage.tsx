"use client";

import { useParams } from "next/navigation";

import {
  BusinessProfileSkeleton,
  BusinessProfileView,
} from "@/features/business/components/BusinessProfileView";
import { RequestToJoinButton } from "@/features/business/components/RequestToJoinButton";
import { FollowButton } from "@/features/network/components/FollowButton";
import { useBusiness } from "@/features/business/hooks/use-business-queries";
import { queryKeys } from "@/lib/query-keys";
import { useQueryClient } from "@tanstack/react-query";

export function BusinessDiscoveryPage() {
  const { slug } = useParams<{ slug: string }>();
  const queryClient = useQueryClient();
  // Always fetch fresh business data on the public discovery page.
  // The default 5-min staleTime is too aggressive here — settings like
  // open_member_request and _relationship may have changed since the last visit.
  const { data: business, isLoading, error } = useBusiness(slug, { staleTime: 0 });

  if (isLoading) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-8">
        <BusinessProfileSkeleton />
      </div>
    );
  }

  if (error || !business) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-16 text-center">
        <h2 className="text-xl font-semibold">Business not found</h2>
        <p className="text-muted-foreground mt-2 text-sm">
          This business profile may not exist or is not accessible.
        </p>
      </div>
    );
  }

  if (!business.profile.is_public) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-16 text-center">
        <h2 className="text-xl font-semibold">Private profile</h2>
        <p className="text-muted-foreground mt-2 text-sm">
          This business profile is not public.
        </p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6 px-4 py-8">
      <BusinessProfileView business={business} />
      <div className="flex flex-wrap gap-3">
        <FollowButton
          followeeType="business"
          followeeId={business.id}
          followStatus={business._relationship?.follow_status ?? null}
          followId={business._relationship?.follow_id ?? null}
          activeFollowTransaction={business._relationship?.active_follow_transaction ?? null}
          onAction={() => queryClient.invalidateQueries({ queryKey: queryKeys.business.detail(slug) })}
        />
        <RequestToJoinButton business={business} />
      </div>
    </div>
  );
}
