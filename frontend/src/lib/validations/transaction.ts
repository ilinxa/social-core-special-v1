import { z } from "zod";

export const createInvitationSchema = z.object({
  transaction_type: z.string().min(1, "Transaction type is required"),
  target_user_id: z.string().uuid("Invalid user ID"),
  context_type: z.string().min(1, "Context type is required"),
  context_id: z.string().uuid("Invalid context ID"),
  role_id: z.string().uuid("Invalid role ID").optional(),
  message: z.string().max(500, "Message must be 500 characters or less").optional(),
});

export const denySchema = z.object({
  reason: z
    .string()
    .max(500, "Reason must be 500 characters or less")
    .optional(),
});

export const requestInfoSchema = z.object({
  message: z
    .string()
    .min(1, "Message is required")
    .max(1000, "Message must be 1000 characters or less"),
  requested_fields: z.array(z.string()).optional(),
});

export const acceptSchema = z.object({
  role_id: z.string().uuid("Invalid role ID").optional(),
});

export type CreateInvitationFormValues = z.infer<typeof createInvitationSchema>;
export type DenyFormValues = z.infer<typeof denySchema>;
export type RequestInfoFormValues = z.infer<typeof requestInfoSchema>;
export type AcceptFormValues = z.infer<typeof acceptSchema>;
