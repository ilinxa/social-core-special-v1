import { z } from "zod";

export const COMPANY_SIZE_OPTIONS = [
  { value: "", label: "Not specified" },
  { value: "1", label: "1 employee" },
  { value: "2-10", label: "2-10 employees" },
  { value: "11-50", label: "11-50 employees" },
  { value: "51-200", label: "51-200 employees" },
  { value: "201-500", label: "201-500 employees" },
  { value: "500+", label: "500+ employees" },
] as const;

export const businessProfileSchema = z.object({
  display_name: z.string().max(255),
  tagline: z.string().max(500),
  description: z.string().max(5000),
  website: z.string().url("Invalid URL").or(z.literal("")),
  contact_email: z.string().email("Invalid email").or(z.literal("")),
  contact_phone: z.string().max(20),
  industry: z.string().max(100),
  company_size: z.string(),
  founded_year: z
    .number()
    .int()
    .min(1800, "Year must be after 1800")
    .max(2100, "Year must be before 2100")
    .nullable(),
  social_links: z.record(z.string(), z.string()),
  tags: z.array(z.string().max(50)).max(20, "Maximum 20 tags"),
  is_public: z.boolean(),
  // Account-level field (managed in same form, sent via separate API)
  city: z.string().max(100),
});

export type BusinessProfileFormValues = z.infer<typeof businessProfileSchema>;
