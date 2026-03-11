import { z } from "zod";

// =============================================================================
// SHARED VALIDATORS
// =============================================================================

const emailField = z.string().email("Enter a valid email address");

const usernameField = z
  .string()
  .min(5, "Username must be at least 5 characters")
  .max(30, "Username must be at most 30 characters")
  .regex(
    /^[a-zA-Z0-9_]+$/,
    "Username can only contain letters, numbers, and underscores",
  );

const passwordField = z
  .string()
  .min(8, "Password must be at least 8 characters")
  .refine((val) => !/^\d+$/.test(val), "Password cannot be entirely numeric")
  .refine((val) => /[A-Z]/.test(val), "Password must contain at least one uppercase letter")
  .refine((val) => /[^a-zA-Z0-9]/.test(val), "Password must contain at least one special character");

// =============================================================================
// AUTH SCHEMAS
// =============================================================================

export const loginSchema = z.object({
  email: emailField,
  password: z.string().min(1, "Password is required"),
});

export const registerSchema = z
  .object({
    email: emailField,
    username: usernameField,
    password: passwordField,
    confirm_password: z.string().min(1, "Please confirm your password"),
    referred_by: z.string().optional(),
  })
  .refine((data) => data.password === data.confirm_password, {
    message: "Passwords do not match",
    path: ["confirm_password"],
  });

export const verifyEmailSchema = z.object({
  email: emailField,
  code: z
    .string()
    .length(6, "Code must be 6 digits")
    .regex(/^\d{6}$/, "Code must be 6 digits"),
});

export const resendVerificationSchema = z.object({
  email: emailField,
});

export const passwordResetSchema = z.object({
  email: emailField,
});

export const passwordResetConfirmSchema = z.object({
  token: z.string().uuid("Invalid reset token"),
  new_password: passwordField,
});

export const passwordChangeSchema = z.object({
  current_password: z.string().min(1, "Current password is required"),
  new_password: passwordField,
});

// =============================================================================
// INFERRED TYPES (used in form components)
// =============================================================================

export type LoginFormValues = z.infer<typeof loginSchema>;
export type RegisterFormValues = z.infer<typeof registerSchema>;
export type VerifyEmailFormValues = z.infer<typeof verifyEmailSchema>;
export type ResendVerificationFormValues = z.infer<typeof resendVerificationSchema>;
export type PasswordResetFormValues = z.infer<typeof passwordResetSchema>;
export type PasswordResetConfirmFormValues = z.infer<typeof passwordResetConfirmSchema>;
export type PasswordChangeFormValues = z.infer<typeof passwordChangeSchema>;
