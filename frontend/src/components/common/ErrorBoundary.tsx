"use client";

import { ErrorBoundary, type FallbackProps } from "react-error-boundary";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { reportError } from "@/lib/error-reporting";

function FeatureErrorFallback({ error, resetErrorBoundary }: FallbackProps) {
  return (
    <Card className="border-destructive/20">
      <CardHeader>
        <CardTitle className="text-destructive text-lg">Something went wrong</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-muted-foreground text-sm">
          {error instanceof Error ? error.message : "An unexpected error occurred"}
        </p>
        <Button variant="outline" size="sm" onClick={resetErrorBoundary}>
          Try again
        </Button>
      </CardContent>
    </Card>
  );
}

export function FeatureErrorBoundary({ children }: { children: React.ReactNode }) {
  return (
    <ErrorBoundary
      FallbackComponent={FeatureErrorFallback}
      onError={(error, info) => {
        reportError(error, { boundary: "feature", componentStack: info.componentStack });
      }}
    >
      {children}
    </ErrorBoundary>
  );
}
