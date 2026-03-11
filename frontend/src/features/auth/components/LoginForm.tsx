"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useForm } from "react-hook-form";

import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { FormField } from "@/components/common/FormField";
import { PasswordInput } from "@/components/common/PasswordInput";
import { handleApiError } from "@/lib/api-error-handler";
import { loginSchema, type LoginFormValues } from "@/lib/validations/auth";
import { useLogin } from "@/features/auth/hooks/use-auth-mutations";
import { OAuthButtons } from "@/features/auth/components/OAuthButtons";

export function LoginForm() {
  const searchParams = useSearchParams();
  const isVerified = searchParams.get("verified") === "true";
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
  });

  const login = useLogin();

  async function onSubmit(values: LoginFormValues) {
    try {
      await login.mutateAsync(values);
    } catch (error) {
      handleApiError<LoginFormValues>(error, {
        setError,
        handlers: {
          invalid_credentials: () => setError("root", { message: "Invalid email or password" }),
          account_not_verified: () =>
            setError("root", { message: "Please verify your email before signing in" }),
          account_inactive: () => setError("root", { message: "Your account has been deactivated" }),
        },
      });
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
      {isVerified && (
        <div role="status" className="rounded-md border border-green-200 bg-green-50 p-3 text-sm text-green-800 dark:border-green-800 dark:bg-green-950 dark:text-green-200">
          Email verified successfully. You can now sign in.
        </div>
      )}

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
        {...register("email")}
      />

      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <Label htmlFor="password">Password</Label>
          <Link href="/forgot-password" className="text-primary text-sm hover:underline">
            Forgot password?
          </Link>
        </div>
        <PasswordInput
          id="password"
          autoComplete="current-password"
          aria-invalid={!!errors.password}
          {...register("password")}
        />
        {errors.password && <p className="text-destructive text-sm">{errors.password.message}</p>}
      </div>

      <Button type="submit" className="w-full" disabled={isSubmitting}>
        {isSubmitting ? "Signing in..." : "Sign In"}
      </Button>

      <OAuthButtons />

      <p className="text-center text-sm">
        Don&apos;t have an account?{" "}
        <Link href="/register" className="text-primary underline">
          Sign up
        </Link>
      </p>
    </form>
  );
}
