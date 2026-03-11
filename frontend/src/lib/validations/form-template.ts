import { z } from "zod";

export const createTemplateSchema = z.object({
  name: z
    .string()
    .min(1, "Form name is required")
    .max(200, "Form name must be 200 characters or less"),
  slug: z
    .string()
    .max(200, "Slug must be 200 characters or less")
    .regex(/^[a-z0-9]+(?:-[a-z0-9]+)*$/, "Slug must be lowercase with hyphens only")
    .optional()
    .or(z.literal("")),
  description: z
    .string()
    .max(1000, "Description must be 1000 characters or less")
    .optional(),
  scope: z.enum(["business", "platform"]),
});

export const createFieldSchema = z.object({
  field_key: z
    .string()
    .min(1, "Field key is required")
    .max(100, "Field key must be 100 characters or less")
    .regex(
      /^[a-z][a-z0-9_]*$/,
      "Field key must start with a letter and contain only lowercase letters, numbers, and underscores",
    ),
  field_type: z.string().min(1, "Field type is required"),
  label: z
    .string()
    .min(1, "Label is required")
    .max(200, "Label must be 200 characters or less"),
  description: z.string().max(500).optional(),
  placeholder: z.string().max(200).optional(),
  is_required: z.boolean().optional(),
});

export const forkTemplateSchema = z.object({
  new_name: z
    .string()
    .max(200, "Form name must be 200 characters or less")
    .optional(),
  new_slug: z
    .string()
    .max(200, "Slug must be 200 characters or less")
    .regex(/^[a-z0-9]+(?:-[a-z0-9]+)*$/, "Slug must be lowercase with hyphens only")
    .optional()
    .or(z.literal("")),
});

export type CreateTemplateFormValues = z.infer<typeof createTemplateSchema>;
export type CreateFieldFormValues = z.infer<typeof createFieldSchema>;
export type ForkTemplateFormValues = z.infer<typeof forkTemplateSchema>;
