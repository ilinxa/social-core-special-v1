"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useSearchParams } from "next/navigation";
import { useForm } from "react-hook-form";

import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { PasswordInput } from "@/components/common/PasswordInput";
import { PasswordStrengthMeter } from "@/components/common/PasswordStrengthMeter";
import { handleApiError } from "@/lib/api-error-handler";
import {
  passwordResetConfirmSchema,
  type PasswordResetConfirmFormValues,
} from "@/lib/validations/auth";
import { usePasswordResetConfirm } from "@/features/auth/hooks/use-auth-mutations";

export function ResetPasswordForm() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token") ?? "";

  const {
    register,
    handleSubmit,
    setError,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<PasswordResetConfirmFormValues>({
    resolver: zodResolver(passwordResetConfirmSchema),
    defaultValues: { token, new_password: "" },
  });

  const passwordValue = watch("new_password", "");

  const resetConfirm = usePasswordResetConfirm();

  async function onSubmit(values: PasswordResetConfirmFormValues) {
    try {
      await resetConfirm.mutateAsync(values);
    } catch (error) {
      handleApiError<PasswordResetConfirmFormValues>(error, {
        setError,
        handlers: {
          not_found: () =>
            setError("root", {
              message: "This reset link is invalid or has expired. Please request a new one.",
            }),
        },
      });
    }
  }

  if (!token) {
    return (
      <div className="text-center">
        <p className="text-destructive text-sm">
          Invalid reset link. Please request a new password reset.
        </p>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
      {errors.root && (
        <div role="alert" className="bg-destructive/10 text-destructive rounded-md p-3 text-sm">
          {errors.root.message}
        </div>
      )}

      <input type="hidden" {...register("token")} />

      <div className="space-y-2">
        <Label htmlFor="new_password">New Password</Label>
        <PasswordInput
          id="new_password"
          autoComplete="new-password"
          aria-invalid={!!errors.new_password}
          {...register("new_password")}
        />
        {errors.new_password && (
          <p className="text-destructive text-sm">{errors.new_password.message}</p>
        )}
        <PasswordStrengthMeter password={passwordValue} />
      </div>

      <Button type="submit" className="w-full" disabled={isSubmitting}>
        {isSubmitting ? "Resetting..." : "Reset Password"}
      </Button>
    </form>
  );
}
