import type { Metadata } from "next";

export const metadata: Metadata = { title: "Contact" };

export default function ContactPage() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-16">
      <h1 className="text-4xl font-bold">Contact Us</h1>
      <p className="mt-4 text-muted-foreground">Contact page coming soon.</p>
    </div>
  );
}
