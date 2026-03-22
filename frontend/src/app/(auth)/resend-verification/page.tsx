import type { Metadata } from "next";

import { ResendVerificationForm } from "@/features/auth/components/ResendVerificationForm";

export const metadata: Metadata = { title: "Resend Verification" };

export default function ResendVerificationPage() {
  return <ResendVerificationForm />;
}
