"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useForm } from "react-hook-form";

import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { FormField } from "@/components/common/FormField";
import { PasswordInput } from "@/components/common/PasswordInput";
import { PasswordStrengthMeter } from "@/components/common/PasswordStrengthMeter";
import { handleApiError } from "@/lib/api-error-handler";
import { registerSchema, type RegisterFormValues } from "@/lib/validations/auth";
import { useRegister } from "@/features/auth/hooks/use-auth-mutations";
import { OAuthButtons } from "@/features/auth/components/OAuthButtons";

export function RegisterForm() {
  const {
    register: registerField,
    handleSubmit,
    setError,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<RegisterFormValues>({
    resolver: zodResolver(registerSchema),
  });

  const passwordValue = watch("password", "");

  const registerMutation = useRegister();

  async function onSubmit(values: RegisterFormValues) {
    try {
      await registerMutation.mutateAsync(values);
    } catch (error) {
      handleApiError<RegisterFormValues>(error, {
        setError,
        handlers: {
          conflict: (err) => {
            if (err.message?.toLowerCase().includes("username")) {
              setError("username", { message: "This username is already taken" });
            } else {
              setError("email", { message: "This email is already registered" });
            }
          },
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
        {...registerField("email")}
      />

      <FormField
        label="Username"
        type="text"
        autoComplete="username"
        placeholder="letters, numbers, and underscores"
        error={errors.username}
        {...registerField("username")}
      />

      <div className="space-y-2">
        <Label htmlFor="password">Password</Label>
        <PasswordInput
          id="password"
          autoComplete="new-password"
          aria-invalid={!!errors.password}
          {...registerField("password")}
        />
        {errors.password && <p className="text-destructive text-sm">{errors.password.message}</p>}
        <PasswordStrengthMeter password={passwordValue} />
      </div>

      <div className="space-y-2">
        <Label htmlFor="confirm_password">Confirm Password</Label>
        <PasswordInput
          id="confirm_password"
          autoComplete="new-password"
          aria-invalid={!!errors.confirm_password}
          {...registerField("confirm_password")}
        />
        {errors.confirm_password && (
          <p className="text-destructive text-sm">{errors.confirm_password.message}</p>
        )}
      </div>

      <Button type="submit" className="w-full" disabled={isSubmitting}>
        {isSubmitting ? "Creating account..." : "Create Account"}
      </Button>

      <OAuthButtons />

      <p className="text-center text-sm">
        Already have an account?{" "}
        <Link href="/login" className="text-primary underline">
          Sign in
        </Link>
      </p>
    </form>
  );
}
