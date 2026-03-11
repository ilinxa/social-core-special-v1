"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { useForm } from "react-hook-form";

import { Button } from "@/components/ui/button";
import { FormField } from "@/components/common/FormField";
import { handleApiError } from "@/lib/api-error-handler";
import { verifyEmailSchema, type VerifyEmailFormValues } from "@/lib/validations/auth";
import { useResendVerification, useVerifyEmail } from "@/features/auth/hooks/use-auth-mutations";

const RESEND_COOLDOWN = 60;

export function VerifyEmailForm() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const emailFromParams = searchParams.get("email") ?? "";
  const [cooldown, setCooldown] = useState(0);

  const {
    register,
    handleSubmit,
    setError,
    getValues,
    formState: { errors, isSubmitting },
  } = useForm<VerifyEmailFormValues>({
    resolver: zodResolver(verifyEmailSchema),
    defaultValues: { email: emailFromParams, code: "" },
  });

  const verifyEmail = useVerifyEmail();
  const resendVerification = useResendVerification();

  useEffect(() => {
    if (cooldown <= 0) return;
    const timer = setTimeout(() => setCooldown((c) => c - 1), 1000);
    return () => clearTimeout(timer);
  }, [cooldown]);

  const handleResend = useCallback(() => {
    const email = getValues("email");
    if (cooldown > 0 || !email) return;
    resendVerification.mutate({ email });
    setCooldown(RESEND_COOLDOWN);
  }, [cooldown, getValues, resendVerification]);

  async function onSubmit(values: VerifyEmailFormValues) {
    try {
      await verifyEmail.mutateAsync(values);
      router.push("/login?verified=true");
    } catch (error) {
      handleApiError<VerifyEmailFormValues>(error, {
        setError,
        handlers: {
          not_found: () =>
            setError("root", { message: "No pending verification found for this email" }),
          invalid_code: () =>
            setError("root", {
              message: "Invalid verification code. Please check the code and try again.",
            }),
          code_expired: () =>
            setError("root", {
              message:
                "Verification code has expired. Please request a new code.",
            }),
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

      <FormField
        label="Email"
        type="email"
        autoComplete="email"
        error={errors.email}
        disabled={!!emailFromParams}
        {...register("email")}
      />

      <FormField
        label="Verification Code"
        type="text"
        inputMode="numeric"
        maxLength={6}
        placeholder="000000"
        autoComplete="one-time-code"
        error={errors.code}
        description="Enter the 6-digit code sent to your email"
        {...register("code")}
      />

      <Button type="submit" className="w-full" disabled={isSubmitting}>
        {isSubmitting ? "Verifying..." : "Verify Email"}
      </Button>

      <div className="text-center">
        <Button
          type="button"
          variant="link"
          disabled={cooldown > 0 || resendVerification.isPending}
          onClick={handleResend}
          className="text-sm"
        >
          {cooldown > 0 ? `Resend code (${cooldown}s)` : "Resend code"}
        </Button>
      </div>
    </form>
  );
}
