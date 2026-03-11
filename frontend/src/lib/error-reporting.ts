export interface ErrorContext {
  /** Error boundary name (e.g., "feature", "app") */
  boundary?: string;
  /** Component that threw */
  component?: string;
  /** Action that triggered the error */
  action?: string;
  /** React error boundary component stack */
  componentStack?: string | null;
  /** Additional context */
  source?: string;
  [key: string]: unknown;
}

export function reportError(error: unknown, context?: ErrorContext): void {
  const errorObj = error instanceof Error ? error : new Error(String(error));

  if (process.env.NODE_ENV === "production") {
    // Sentry.captureException(errorObj, { extra: context });
  }

  console.error("[Error]", errorObj, context);
}
