import { z } from "zod";

export const createRoleSchema = z.object({
  name: z
    .string()
    .min(1, "Role name is required")
    .max(100, "Role name must be 100 characters or less"),
  level: z
    .number({ error: "Level is required" })
    .int("Level must be a whole number")
    .min(1, "Level must be at least 1")
    .max(100, "Level must be at most 100"),
  description: z.string().max(500, "Description must be 500 characters or less").optional(),
});

export const updateRoleSchema = z.object({
  name: z
    .string()
    .min(1, "Role name is required")
    .max(100, "Role name must be 100 characters or less")
    .optional(),
  description: z.string().max(500, "Description must be 500 characters or less").optional(),
});

export type CreateRoleFormValues = z.infer<typeof createRoleSchema>;
export type UpdateRoleFormValues = z.infer<typeof updateRoleSchema>;
