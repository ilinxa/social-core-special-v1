import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = { title: "Welcome" };

export default function LandingPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4">
      <h1 className="text-4xl font-bold">Welcome to SocialMedia Adv</h1>
      <Link href="/login" className="text-primary underline hover:no-underline">
        Sign in to get started
      </Link>
    </div>
  );
}
