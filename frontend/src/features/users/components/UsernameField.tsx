"use client";

import { forwardRef } from "react";
import { CheckCircle, Loader2, XCircle } from "lucide-react";
import type { Control, FieldError } from "react-hook-form";
import { useWatch } from "react-hook-form";

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import { useUsernameCheck } from "@/features/users/hooks/use-username-check";

interface UsernameFieldProps extends Omit<React.ComponentProps<typeof Input>, "type"> {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  control: Control<any>;
  currentUsername: string;
  error?: FieldError;
}

export const UsernameField = forwardRef<HTMLInputElement, UsernameFieldProps>(
  ({ control, currentUsername, error, ...inputProps }, ref) => {
    const watchedUsername = useWatch({ control, name: "username" }) ?? "";
    const { isChecking, isAvailable, isCurrent } = useUsernameCheck(watchedUsername, currentUsername);

    const showAvailable = !isChecking && isAvailable === true && !isCurrent;
    const showTaken = !isChecking && isAvailable === false;

    return (
      <div className="space-y-2">
        <Label htmlFor="username">Username</Label>
        <div className="relative">
          <span className="text-muted-foreground pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-sm select-none">
            @
          </span>
          <Input
            ref={ref}
            id="username"
            className={cn(
              "pl-7 pr-10",
              showAvailable && "border-success focus-visible:border-success focus-visible:ring-success/20",
              showTaken && "border-destructive focus-visible:border-destructive focus-visible:ring-destructive/20",
            )}
            aria-invalid={!!error || showTaken}
            aria-describedby={error ? "username-error" : undefined}
            {...inputProps}
          />
          <div className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2">
            {isChecking && <Loader2 className="text-muted-foreground h-4 w-4 animate-spin" />}
            {showAvailable && <CheckCircle className="h-4 w-4 text-success" />}
            {showTaken && <XCircle className="h-4 w-4 text-destructive" />}
          </div>
        </div>

        {/* Status message */}
        {showAvailable && (
          <p className="text-success flex items-center gap-1.5 text-xs font-medium">
            <CheckCircle className="h-3 w-3" />
            Available
          </p>
        )}
        {showTaken && (
          <p className="text-destructive flex items-center gap-1.5 text-xs font-medium">
            <XCircle className="h-3 w-3" />
            Username taken
          </p>
        )}
        {error && (
          <p id="username-error" className="text-destructive text-sm">
            {error.message}
          </p>
        )}
      </div>
    );
  },
);

UsernameField.displayName = "UsernameField";
