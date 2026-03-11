"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useState } from "react";
import { useForm } from "react-hook-form";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { FormField } from "@/components/common/FormField";
import { handleApiError } from "@/lib/api-error-handler";
import {
  resendVerificationSchema,
  type ResendVerificationFormValues,
} from "@/lib/validations/auth";
import { useResendVerification } from "@/features/auth/hooks/use-auth-mutations";

export default function ResendVerificationPage() {
  const [isSubmitted, setIsSubmitted] = useState(false);

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<ResendVerificationFormValues>({
    resolver: zodResolver(resendVerificationSchema),
  });

  const resend = useResendVerification();

  async function onSubmit(values: ResendVerificationFormValues) {
    try {
      await resend.mutateAsync(values);
      setIsSubmitted(true);
    } catch (error) {
      handleApiError<ResendVerificationFormValues>(error, { setError });
    }
  }

  return (
    <Card>
      <CardHeader className="text-center">
        <CardTitle className="text-2xl">Resend Verification</CardTitle>
        <CardDescription>Enter your email to receive a new verification code</CardDescription>
      </CardHeader>
      <CardContent>
        {isSubmitted ? (
          <div className="space-y-4 text-center">
            <p className="text-sm">
              If an account exists with that email, we&apos;ve sent a new verification code.
            </p>
            <Link href="/verify-email" className="text-primary text-sm underline">
              Enter verification code
            </Link>
          </div>
        ) : (
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
            {errors.root && (
              <div
                role="alert"
                className="bg-destructive/10 text-destructive rounded-md p-3 text-sm"
              >
                {errors.root.message}
              </div>
            )}

            <FormField
              label="Email"
              type="email"
              autoComplete="email"
              error={errors.email}
              {...register("email")}
            />

            <Button type="submit" className="w-full" disabled={isSubmitting}>
              {isSubmitting ? "Sending..." : "Resend Verification"}
            </Button>

            <p className="text-center text-sm">
              <Link href="/login" className="text-primary underline">
                Back to sign in
              </Link>
            </p>
          </form>
        )}
      </CardContent>
    </Card>
  );
}
