import { toast } from "sonner";

import { ApiError } from "@/lib/api-client";
import { reportError } from "@/lib/error-reporting";

import type { UseFormSetError, FieldValues, Path } from "react-hook-form";

type ErrorCodeHandler = (error: ApiError) => void;

interface HandleApiErrorOptions<T extends FieldValues> {
  /** react-hook-form setError — maps validation errors to form fields */
  setError?: UseFormSetError<T>;
  /** Show fallback errors as toasts instead of form root errors */
  showToast?: boolean;
  /** Custom handlers keyed by ApiError.code (e.g., "invalid_credentials") */
  handlers?: Record<string, ErrorCodeHandler>;
}

/**
 * Centralized API error handler for forms and mutations.
 *
 * Priority: custom handlers → validation mapping → rate limiting → fallback.
 */
export function handleApiError<T extends FieldValues>(
  error: unknown,
  options: HandleApiErrorOptions<T> = {},
): void {
  const { setError, showToast = false, handlers } = options;

  if (!(error instanceof ApiError)) {
    reportError(error, { source: "handleApiError" });
    if (showToast) {
      toast.error("An unexpected error occurred");
    } else if (setError) {
      setError("root" as Path<T>, { message: "An unexpected error occurred" });
    }
    return;
  }

  // 1. Custom handlers by error code
  if (handlers && error.code in handlers) {
    handlers[error.code](error);
    return;
  }

  // 2. Validation errors → map to form fields
  if (error.isValidation && error.details && setError) {
    for (const [field, messages] of Object.entries(error.details)) {
      setError(field as Path<T>, {
        message: Array.isArray(messages) ? String(messages[0]) : String(messages),
      });
    }
    return;
  }

  // 3. Rate limiting
  if (error.isRateLimited) {
    const retryAfter = error.retryAfter ?? 60;
    const message = `Too many attempts. Try again in ${retryAfter} seconds.`;
    if (showToast) {
      toast.error(message);
    } else if (setError) {
      setError("root" as Path<T>, { message });
    }
    return;
  }

  // 4. Fallback
  if (showToast) {
    toast.error(error.message);
  } else if (setError) {
    setError("root" as Path<T>, { message: error.message });
  }
}
