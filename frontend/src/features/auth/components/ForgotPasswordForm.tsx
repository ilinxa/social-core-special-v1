"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useState } from "react";
import { useForm } from "react-hook-form";

import { Button } from "@/components/ui/button";
import { FormField } from "@/components/common/FormField";
import { handleApiError } from "@/lib/api-error-handler";
import { passwordResetSchema, type PasswordResetFormValues } from "@/lib/validations/auth";
import { usePasswordReset } from "@/features/auth/hooks/use-auth-mutations";

export function ForgotPasswordForm() {
  const [isSubmitted, setIsSubmitted] = useState(false);

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<PasswordResetFormValues>({
    resolver: zodResolver(passwordResetSchema),
  });

  const passwordReset = usePasswordReset();

  async function onSubmit(values: PasswordResetFormValues) {
    try {
      await passwordReset.mutateAsync(values);
      setIsSubmitted(true);
    } catch (error) {
      handleApiError<PasswordResetFormValues>(error, { setError });
    }
  }

  if (isSubmitted) {
    return (
      <div className="space-y-4 text-center">
        <p className="text-sm">
          If an account exists with that email, we&apos;ve sent a password reset link. Please check
          your inbox.
        </p>
        <Link href="/login" className="text-primary text-sm underline">
          Back to sign in
        </Link>
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

      <FormField
        label="Email"
        type="email"
        autoComplete="email"
        error={errors.email}
        description="We'll send you a link to reset your password"
        {...register("email")}
      />

      <Button type="submit" className="w-full" disabled={isSubmitting}>
        {isSubmitting ? "Sending..." : "Send Reset Link"}
      </Button>

      <p className="text-center text-sm">
        <Link href="/login" className="text-primary underline">
          Back to sign in
        </Link>
      </p>
    </form>
  );
}
