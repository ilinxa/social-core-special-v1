import { describe, it, expect } from "vitest";

import { platformProfileSchema } from "./platform-profile";

const validData = {
  name: "My Platform",
  tagline: "The best platform",
  description: "A platform for everything.",
  primary_color: "#FF5733",
  secondary_color: "#33FF57",
  contact_email: "admin@platform.com",
  contact_phone: "+1234567890",
  address: "123 Main St",
  social_links: { twitter: "https://twitter.com/platform" },
};

describe("platformProfileSchema", () => {
  it("validates a complete valid object", () => {
    const result = platformProfileSchema.safeParse(validData);
    expect(result.success).toBe(true);
  });

  it("requires name (min 1 char)", () => {
    const result = platformProfileSchema.safeParse({
      ...validData,
      name: "",
    });
    expect(result.success).toBe(false);
  });

  it("accepts name at max length (255)", () => {
    const result = platformProfileSchema.safeParse({
      ...validData,
      name: "a".repeat(255),
    });
    expect(result.success).toBe(true);
  });

  it("rejects name over 255 characters", () => {
    const result = platformProfileSchema.safeParse({
      ...validData,
      name: "a".repeat(256),
    });
    expect(result.success).toBe(false);
  });

  it("validates hex color format for primary_color", () => {
    const validColors = ["#000000", "#FFFFFF", "#ff5733", "#aAbBcC"];
    for (const color of validColors) {
      const result = platformProfileSchema.safeParse({
        ...validData,
        primary_color: color,
      });
      expect(result.success).toBe(true);
    }
  });

  it("rejects invalid hex color for primary_color", () => {
    const invalidColors = ["red", "#FFF", "FF5733", "#GGGGGG", "#12345", "#1234567", ""];
    for (const color of invalidColors) {
      const result = platformProfileSchema.safeParse({
        ...validData,
        primary_color: color,
      });
      expect(result.success).toBe(false);
    }
  });

  it("validates hex color format for secondary_color", () => {
    const validColors = ["#000000", "#FFFFFF", "#abcdef"];
    for (const color of validColors) {
      const result = platformProfileSchema.safeParse({
        ...validData,
        secondary_color: color,
      });
      expect(result.success).toBe(true);
    }
  });

  it("rejects invalid hex color for secondary_color", () => {
    const invalidColors = ["blue", "#GGG", "123456", ""];
    for (const color of invalidColors) {
      const result = platformProfileSchema.safeParse({
        ...validData,
        secondary_color: color,
      });
      expect(result.success).toBe(false);
    }
  });

  it("accepts empty string for contact_email", () => {
    const result = platformProfileSchema.safeParse({
      ...validData,
      contact_email: "",
    });
    expect(result.success).toBe(true);
  });

  it("accepts valid email for contact_email", () => {
    const result = platformProfileSchema.safeParse({
      ...validData,
      contact_email: "test@example.com",
    });
    expect(result.success).toBe(true);
  });

  it("rejects invalid email for contact_email", () => {
    const result = platformProfileSchema.safeParse({
      ...validData,
      contact_email: "not-an-email",
    });
    expect(result.success).toBe(false);
  });

  it("rejects tagline over 500 characters", () => {
    const result = platformProfileSchema.safeParse({
      ...validData,
      tagline: "a".repeat(501),
    });
    expect(result.success).toBe(false);
  });

  it("rejects description over 5000 characters", () => {
    const result = platformProfileSchema.safeParse({
      ...validData,
      description: "a".repeat(5001),
    });
    expect(result.success).toBe(false);
  });

  it("rejects contact_phone over 20 characters", () => {
    const result = platformProfileSchema.safeParse({
      ...validData,
      contact_phone: "1".repeat(21),
    });
    expect(result.success).toBe(false);
  });

  it("rejects address over 500 characters", () => {
    const result = platformProfileSchema.safeParse({
      ...validData,
      address: "a".repeat(501),
    });
    expect(result.success).toBe(false);
  });

  it("accepts empty social_links record", () => {
    const result = platformProfileSchema.safeParse({
      ...validData,
      social_links: {},
    });
    expect(result.success).toBe(true);
  });
});
