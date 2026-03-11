import { z } from "zod";

export const BUSINESS_TYPE_OPTIONS = [
  { value: "", label: "Select type..." },
  { value: "sole_proprietorship", label: "Sole Proprietorship" },
  { value: "partnership", label: "Partnership" },
  { value: "llc", label: "LLC" },
  { value: "corporation", label: "Corporation" },
  { value: "nonprofit", label: "Nonprofit" },
  { value: "cooperative", label: "Cooperative" },
  { value: "other", label: "Other" },
] as const;

export const createBusinessSchema = z.object({
  legal_name: z.string().min(1, "Legal name is required").max(255, "Max 255 characters"),
  country: z.string().min(1, "Country is required"),
  slug: z
    .string()
    .regex(/^[a-z0-9]+(?:-[a-z0-9]+)*$/, "Only lowercase letters, numbers, and hyphens")
    .min(3, "Min 3 characters")
    .max(50, "Max 50 characters")
    .optional()
    .or(z.literal("")),
  business_type: z.string().optional(),
  display_name: z.string().max(255, "Max 255 characters").optional().or(z.literal("")),
});

export type CreateBusinessFormValues = z.infer<typeof createBusinessSchema>;
