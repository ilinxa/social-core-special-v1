import { z } from "zod";

// =============================================================================
// PROFILE EDIT SCHEMA
// =============================================================================

export const editProfileSchema = z.object({
  first_name: z.string().max(150, "First name too long"),
  last_name: z.string().max(150, "Last name too long"),
  phone: z.string().max(20, "Phone number too long"),
  bio: z.string().max(500, "Bio must be 500 characters or less"),
  timezone: z.string().min(1, "Timezone is required"),
  language: z.string().min(1, "Language is required").max(10),
  country: z.string().max(2),
  city: z.string().max(100),
  tags: z.array(z.string().max(50)).max(20, "Maximum 20 tags"),
  is_public: z.boolean(),
});

// =============================================================================
// USERNAME SCHEMA (used in Settings page)
// =============================================================================

export const usernameSchema = z.object({
  username: z
    .string()
    .min(5, "Username must be at least 5 characters")
    .max(30, "Username must be at most 30 characters")
    .regex(/^[a-zA-Z0-9_]+$/, "Only letters, numbers, and underscores"),
});

// =============================================================================
// INFERRED TYPES
// =============================================================================

export type EditProfileFormValues = z.infer<typeof editProfileSchema>;
export type UsernameFormValues = z.infer<typeof usernameSchema>;
