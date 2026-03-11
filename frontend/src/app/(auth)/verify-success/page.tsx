import type { Metadata } from "next";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export const metadata: Metadata = {
  title: "Email Verified",
};

export default function VerifySuccessPage() {
  return (
    <Card>
      <CardHeader className="text-center">
        <CardTitle className="text-2xl">Email Verified</CardTitle>
        <CardDescription>Your email has been successfully verified</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4 text-center">
        <p className="text-muted-foreground text-sm">
          You can now sign in to your account with full access.
        </p>
        <Button asChild className="w-full">
          <Link href="/login">Sign In</Link>
        </Button>
      </CardContent>
    </Card>
  );
}
