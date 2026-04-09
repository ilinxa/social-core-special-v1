"use client";

import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Shield } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { FormField } from "@/components/common/FormField";
import { PasswordInput } from "@/components/common/PasswordInput";
import { handleApiError } from "@/lib/api-error-handler";
import { isGovernanceTokenValid } from "@/lib/governance-token";
import {
  governancePasswordAuthApi,
  governanceOtpSendApi,
  governanceOtpVerifyApi,
} from "@/features/governance/api/governance-auth-api";

// =============================================================================
// VALIDATION SCHEMAS
// =============================================================================

const passwordSchema = z.object({
  password: z.string().min(1, "Password is required"),
});

const otpSchema = z.object({
  code: z
    .string()
    .length(6, "Code must be 6 digits")
    .regex(/^\d{6}$/, "Code must be 6 digits"),
});

type PasswordFormValues = z.infer<typeof passwordSchema>;
type OtpFormValues = z.infer<typeof otpSchema>;

// =============================================================================
// PAGE
// =============================================================================

export default function GovernanceAuthenticatePage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const callbackUrl = searchParams.get("callbackUrl") || "/gconsole/dashboard";

  // Redirect if already authenticated
  if (typeof window !== "undefined" && isGovernanceTokenValid()) {
    router.replace(callbackUrl);
    return null;
  }

  return (
    <div className="flex min-h-[60vh] items-center justify-center">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="mx-auto mb-2 flex h-12 w-12 items-center justify-center rounded-full bg-amber-100 dark:bg-amber-900">
            <Shield className="h-6 w-6 text-amber-600 dark:text-amber-400" />
          </div>
          <CardTitle>Governance Console</CardTitle>
          <CardDescription>
            This requires re-authentication for security. Your standard session
            is not affected.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="password">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="password">Password</TabsTrigger>
              <TabsTrigger value="otp">Email Code</TabsTrigger>
            </TabsList>
            <TabsContent value="password">
              <PasswordTab callbackUrl={callbackUrl} />
            </TabsContent>
            <TabsContent value="otp">
              <OtpTab callbackUrl={callbackUrl} />
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  );
}

// =============================================================================
// PASSWORD TAB
// =============================================================================

function PasswordTab({ callbackUrl }: { callbackUrl: string }) {
  const router = useRouter();
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<PasswordFormValues>({
    resolver: zodResolver(passwordSchema),
  });

  async function onSubmit(values: PasswordFormValues) {
    try {
      await governancePasswordAuthApi(values.password);
      router.replace(callbackUrl);
    } catch (error) {
      handleApiError<PasswordFormValues>(error, {
        setError,
        handlers: {
          invalid_credentials: () =>
            setError("password", { message: "Incorrect password" }),
          account_locked: () =>
            setError("root", {
              message: "Account locked due to too many failed attempts",
            }),
          permission_denied: () =>
            setError("root", {
              message: "You do not have governance access",
            }),
        },
      });
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="mt-4 space-y-4" noValidate>
      {errors.root && (
        <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-800 dark:border-red-800 dark:bg-red-950 dark:text-red-200">
          {errors.root.message}
        </div>
      )}
      <div className="space-y-2">
        <Label htmlFor="gov-password">Password</Label>
        <PasswordInput
          id="gov-password"
          aria-invalid={!!errors.password}
          {...register("password")}
          autoComplete="current-password"
          autoFocus
        />
        {errors.password && (
          <p className="text-destructive text-sm">{errors.password.message}</p>
        )}
      </div>
      <Button type="submit" className="w-full" disabled={isSubmitting}>
        {isSubmitting ? "Authenticating..." : "Enter Governance Console"}
      </Button>
    </form>
  );
}

// =============================================================================
// OTP TAB
// =============================================================================

function OtpTab({ callbackUrl }: { callbackUrl: string }) {
  const router = useRouter();
  const [otpSent, setOtpSent] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [sendError, setSendError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<OtpFormValues>({
    resolver: zodResolver(otpSchema),
  });

  async function handleSendOtp() {
    setIsSending(true);
    setSendError(null);
    try {
      await governanceOtpSendApi();
      setOtpSent(true);
    } catch (error: unknown) {
      const apiError = error as { response?: { data?: { error?: { code?: string } } } };
      const code = apiError?.response?.data?.error?.code;
      if (code === "permission_denied") {
        setSendError("You do not have governance access");
      } else {
        setSendError("Failed to send code. Please try again.");
      }
    } finally {
      setIsSending(false);
    }
  }

  async function onSubmit(values: OtpFormValues) {
    try {
      await governanceOtpVerifyApi(values.code);
      router.replace(callbackUrl);
    } catch (error) {
      handleApiError<OtpFormValues>(error, {
        setError,
        handlers: {
          token_invalid: () =>
            setError("code", { message: "Invalid code" }),
          token_expired: () =>
            setError("code", { message: "Code has expired. Request a new one." }),
          permission_denied: () =>
            setError("root", {
              message: "Too many attempts or no governance access",
            }),
        },
      });
    }
  }

  if (!otpSent) {
    return (
      <div className="mt-4 space-y-4">
        {sendError && (
          <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-800 dark:border-red-800 dark:bg-red-950 dark:text-red-200">
            {sendError}
          </div>
        )}
        <p className="text-muted-foreground text-sm">
          A 6-digit code will be sent to your registered email address.
        </p>
        <Button
          type="button"
          className="w-full"
          onClick={handleSendOtp}
          disabled={isSending}
        >
          {isSending ? "Sending..." : "Send Code"}
        </Button>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="mt-4 space-y-4" noValidate>
      {errors.root && (
        <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-800 dark:border-red-800 dark:bg-red-950 dark:text-red-200">
          {errors.root.message}
        </div>
      )}
      <FormField
        label="6-Digit Code"
        error={errors.code}
        {...register("code")}
        id="gov-otp"
        placeholder="000000"
        maxLength={6}
        inputMode="numeric"
        autoComplete="one-time-code"
        autoFocus
      />
      <Button type="submit" className="w-full" disabled={isSubmitting}>
        {isSubmitting ? "Verifying..." : "Verify & Enter Console"}
      </Button>
      <Button
        type="button"
        variant="ghost"
        className="w-full"
        onClick={handleSendOtp}
        disabled={isSending}
      >
        {isSending ? "Sending..." : "Resend Code"}
      </Button>
    </form>
  );
}
