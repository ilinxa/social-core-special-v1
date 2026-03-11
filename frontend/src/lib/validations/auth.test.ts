import { describe, it, expect } from "vitest";

import {
  loginSchema,
  registerSchema,
  verifyEmailSchema,
  resendVerificationSchema,
  passwordResetSchema,
  passwordResetConfirmSchema,
  passwordChangeSchema,
} from "./auth";

describe("loginSchema", () => {
  it("accepts valid data", () => {
    const result = loginSchema.safeParse({ email: "test@example.com", password: "password123" });
    expect(result.success).toBe(true);
  });

  it("rejects invalid email", () => {
    const result = loginSchema.safeParse({ email: "not-an-email", password: "password123" });
    expect(result.success).toBe(false);
  });

  it("rejects empty password", () => {
    const result = loginSchema.safeParse({ email: "test@example.com", password: "" });
    expect(result.success).toBe(false);
  });
});

describe("registerSchema", () => {
  const validRegisterData = {
    email: "test@example.com",
    username: "testuser",
    password: "Password123!",
    confirm_password: "Password123!",
  };

  it("accepts valid data", () => {
    const result = registerSchema.safeParse(validRegisterData);
    expect(result.success).toBe(true);
  });

  it("accepts optional referred_by", () => {
    const result = registerSchema.safeParse({
      ...validRegisterData,
      referred_by: "REF123",
    });
    expect(result.success).toBe(true);
  });

  it("rejects password shorter than 8 characters", () => {
    const result = registerSchema.safeParse({
      ...validRegisterData,
      password: "Short1!",
      confirm_password: "Short1!",
    });
    expect(result.success).toBe(false);
  });

  it("rejects entirely numeric password", () => {
    const result = registerSchema.safeParse({
      ...validRegisterData,
      password: "12345678",
      confirm_password: "12345678",
    });
    expect(result.success).toBe(false);
  });

  it("rejects password without uppercase letter", () => {
    const result = registerSchema.safeParse({
      ...validRegisterData,
      password: "password123!",
      confirm_password: "password123!",
    });
    expect(result.success).toBe(false);
  });

  it("rejects password without special character", () => {
    const result = registerSchema.safeParse({
      ...validRegisterData,
      password: "Password123",
      confirm_password: "Password123",
    });
    expect(result.success).toBe(false);
  });

  it("rejects mismatched passwords", () => {
    const result = registerSchema.safeParse({
      ...validRegisterData,
      confirm_password: "DifferentPass1!",
    });
    expect(result.success).toBe(false);
  });

  it("rejects username shorter than 5 characters", () => {
    const result = registerSchema.safeParse({
      ...validRegisterData,
      username: "abcd",
    });
    expect(result.success).toBe(false);
  });
});

describe("verifyEmailSchema", () => {
  it("accepts valid 6-digit code", () => {
    const result = verifyEmailSchema.safeParse({
      email: "test@example.com",
      code: "123456",
    });
    expect(result.success).toBe(true);
  });

  it("rejects code with wrong length", () => {
    const result = verifyEmailSchema.safeParse({
      email: "test@example.com",
      code: "12345",
    });
    expect(result.success).toBe(false);
  });

  it("rejects non-numeric code", () => {
    const result = verifyEmailSchema.safeParse({
      email: "test@example.com",
      code: "abcdef",
    });
    expect(result.success).toBe(false);
  });
});

describe("resendVerificationSchema", () => {
  it("accepts valid email", () => {
    const result = resendVerificationSchema.safeParse({ email: "test@example.com" });
    expect(result.success).toBe(true);
  });

  it("rejects invalid email", () => {
    const result = resendVerificationSchema.safeParse({ email: "bad" });
    expect(result.success).toBe(false);
  });
});

describe("passwordResetSchema", () => {
  it("accepts valid email", () => {
    const result = passwordResetSchema.safeParse({ email: "test@example.com" });
    expect(result.success).toBe(true);
  });
});

describe("passwordResetConfirmSchema", () => {
  it("accepts valid data", () => {
    const result = passwordResetConfirmSchema.safeParse({
      token: "550e8400-e29b-41d4-a716-446655440000",
      new_password: "NewPassword123!",
    });
    expect(result.success).toBe(true);
  });

  it("rejects non-UUID token", () => {
    const result = passwordResetConfirmSchema.safeParse({
      token: "not-a-uuid",
      new_password: "NewPassword123!",
    });
    expect(result.success).toBe(false);
  });

  it("rejects short password", () => {
    const result = passwordResetConfirmSchema.safeParse({
      token: "550e8400-e29b-41d4-a716-446655440000",
      new_password: "Short1!",
    });
    expect(result.success).toBe(false);
  });

  it("rejects all-numeric password", () => {
    const result = passwordResetConfirmSchema.safeParse({
      token: "550e8400-e29b-41d4-a716-446655440000",
      new_password: "12345678",
    });
    expect(result.success).toBe(false);
  });
});

describe("passwordChangeSchema", () => {
  it("accepts valid data", () => {
    const result = passwordChangeSchema.safeParse({
      current_password: "oldpassword",
      new_password: "NewPassword123!",
    });
    expect(result.success).toBe(true);
  });

  it("rejects empty current password", () => {
    const result = passwordChangeSchema.safeParse({
      current_password: "",
      new_password: "NewPassword123!",
    });
    expect(result.success).toBe(false);
  });

  it("rejects short new password", () => {
    const result = passwordChangeSchema.safeParse({
      current_password: "oldpassword",
      new_password: "Short1!",
    });
    expect(result.success).toBe(false);
  });
});
