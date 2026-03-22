import type { Metadata } from "next";
import { Suspense } from "react";

import { FeatureErrorBoundary } from "@/components/common/ErrorBoundary";
import { ExplorePage } from "@/features/explore/components/ExplorePage";

export const metadata: Metadata = { title: "Explore" };

export default function ExploreRoute() {
  return (
    <Suspense>
      <FeatureErrorBoundary>
        <ExplorePage />
      </FeatureErrorBoundary>
    </Suspense>
  );
}
