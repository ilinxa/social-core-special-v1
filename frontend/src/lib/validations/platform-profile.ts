import { z } from "zod";

const hexColorRegex = /^#[0-9A-Fa-f]{6}$/;

export const platformProfileSchema = z.object({
  name: z.string().min(1, "Name is required").max(255),
  tagline: z.string().max(500),
  description: z.string().max(5000),
  primary_color: z.string().regex(hexColorRegex, "Invalid hex color"),
  secondary_color: z.string().regex(hexColorRegex, "Invalid hex color"),
  contact_email: z.string().email("Invalid email").or(z.literal("")),
  contact_phone: z.string().max(20),
  address: z.string().max(500),
  social_links: z.record(z.string(), z.string()),
});

export type PlatformProfileFormValues = z.infer<typeof platformProfileSchema>;
