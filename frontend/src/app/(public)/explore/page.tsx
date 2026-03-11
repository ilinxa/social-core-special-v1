import { Suspense } from "react";

import { FeatureErrorBoundary } from "@/components/common/ErrorBoundary";
import { ExplorePage } from "@/features/explore/components/ExplorePage";

export default function ExploreRoute() {
  return (
    <Suspense>
      <FeatureErrorBoundary>
        <ExplorePage />
      </FeatureErrorBoundary>
    </Suspense>
  );
}
