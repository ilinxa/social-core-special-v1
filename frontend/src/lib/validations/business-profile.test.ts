import { describe, it, expect } from "vitest";

import { businessProfileSchema } from "./business-profile";

const validData = {
  display_name: "Acme Corp",
  tagline: "Building the future",
  description: "We build things.",
  website: "https://acme.com",
  contact_email: "info@acme.com",
  contact_phone: "+1234567890",
  industry: "Technology",
  company_size: "11-50",
  founded_year: 2020,
  social_links: { twitter: "https://twitter.com/acme" },
  tags: ["technology", "saas"],
  is_public: true,
  city: "San Francisco",
};

describe("businessProfileSchema", () => {
  it("validates a complete valid object", () => {
    const result = businessProfileSchema.safeParse(validData);
    expect(result.success).toBe(true);
  });

  it("rejects display_name over 255 characters", () => {
    const result = businessProfileSchema.safeParse({
      ...validData,
      display_name: "a".repeat(256),
    });
    expect(result.success).toBe(false);
  });

  it("accepts display_name at 255 characters", () => {
    const result = businessProfileSchema.safeParse({
      ...validData,
      display_name: "a".repeat(255),
    });
    expect(result.success).toBe(true);
  });

  it("rejects tagline over 500 characters", () => {
    const result = businessProfileSchema.safeParse({
      ...validData,
      tagline: "a".repeat(501),
    });
    expect(result.success).toBe(false);
  });

  it("rejects description over 5000 characters", () => {
    const result = businessProfileSchema.safeParse({
      ...validData,
      description: "a".repeat(5001),
    });
    expect(result.success).toBe(false);
  });

  it("accepts valid URL for website", () => {
    const result = businessProfileSchema.safeParse({
      ...validData,
      website: "https://example.com",
    });
    expect(result.success).toBe(true);
  });

  it("accepts empty string for website", () => {
    const result = businessProfileSchema.safeParse({
      ...validData,
      website: "",
    });
    expect(result.success).toBe(true);
  });

  it("rejects invalid URL for website", () => {
    const result = businessProfileSchema.safeParse({
      ...validData,
      website: "not a url",
    });
    expect(result.success).toBe(false);
  });

  it("accepts valid email for contact_email", () => {
    const result = businessProfileSchema.safeParse({
      ...validData,
      contact_email: "test@example.com",
    });
    expect(result.success).toBe(true);
  });

  it("accepts empty string for contact_email", () => {
    const result = businessProfileSchema.safeParse({
      ...validData,
      contact_email: "",
    });
    expect(result.success).toBe(true);
  });

  it("rejects invalid email for contact_email", () => {
    const result = businessProfileSchema.safeParse({
      ...validData,
      contact_email: "bad-email",
    });
    expect(result.success).toBe(false);
  });

  it("accepts null for founded_year", () => {
    const result = businessProfileSchema.safeParse({
      ...validData,
      founded_year: null,
    });
    expect(result.success).toBe(true);
  });

  it("rejects founded_year below 1800", () => {
    const result = businessProfileSchema.safeParse({
      ...validData,
      founded_year: 1799,
    });
    expect(result.success).toBe(false);
  });

  it("accepts founded_year at 1800", () => {
    const result = businessProfileSchema.safeParse({
      ...validData,
      founded_year: 1800,
    });
    expect(result.success).toBe(true);
  });

  it("rejects founded_year above 2100", () => {
    const result = businessProfileSchema.safeParse({
      ...validData,
      founded_year: 2101,
    });
    expect(result.success).toBe(false);
  });

  it("accepts founded_year at 2100", () => {
    const result = businessProfileSchema.safeParse({
      ...validData,
      founded_year: 2100,
    });
    expect(result.success).toBe(true);
  });

  it("rejects non-integer founded_year", () => {
    const result = businessProfileSchema.safeParse({
      ...validData,
      founded_year: 2020.5,
    });
    expect(result.success).toBe(false);
  });

  it("accepts empty social_links record", () => {
    const result = businessProfileSchema.safeParse({
      ...validData,
      social_links: {},
    });
    expect(result.success).toBe(true);
  });

  it("rejects contact_phone over 20 characters", () => {
    const result = businessProfileSchema.safeParse({
      ...validData,
      contact_phone: "1".repeat(21),
    });
    expect(result.success).toBe(false);
  });

  it("rejects industry over 100 characters", () => {
    const result = businessProfileSchema.safeParse({
      ...validData,
      industry: "a".repeat(101),
    });
    expect(result.success).toBe(false);
  });
});
