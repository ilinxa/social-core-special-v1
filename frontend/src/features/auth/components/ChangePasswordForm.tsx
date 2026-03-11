"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";

import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { PasswordInput } from "@/components/common/PasswordInput";
import { PasswordStrengthMeter } from "@/components/common/PasswordStrengthMeter";
import { handleApiError } from "@/lib/api-error-handler";
import { passwordChangeSchema, type PasswordChangeFormValues } from "@/lib/validations/auth";
import { usePasswordChange } from "@/features/auth/hooks/use-auth-mutations";

export function ChangePasswordForm() {
  const {
    register,
    handleSubmit,
    setError,
    reset,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<PasswordChangeFormValues>({
    resolver: zodResolver(passwordChangeSchema),
  });

  const passwordValue = watch("new_password", "");

  const changePassword = usePasswordChange();

  async function onSubmit(values: PasswordChangeFormValues) {
    try {
      await changePassword.mutateAsync(values);
      reset();
    } catch (error) {
      handleApiError<PasswordChangeFormValues>(error, {
        setError,
        handlers: {
          invalid_credentials: () =>
            setError("current_password", { message: "Current password is incorrect" }),
          business_rule_violation: () =>
            setError("current_password", { message: "Current password is incorrect" }),
        },
      });
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
      {errors.root && (
        <div role="alert" className="bg-destructive/10 text-destructive rounded-md p-3 text-sm">
          {errors.root.message}
        </div>
      )}

      <div className="space-y-2">
        <Label htmlFor="current_password">Current Password</Label>
        <PasswordInput
          id="current_password"
          autoComplete="current-password"
          aria-invalid={!!errors.current_password}
          {...register("current_password")}
        />
        {errors.current_password && (
          <p className="text-destructive text-sm">{errors.current_password.message}</p>
        )}
      </div>

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
        {isSubmitting ? "Changing..." : "Change Password"}
      </Button>
    </form>
  );
}
