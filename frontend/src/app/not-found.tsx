import Link from "next/link";

import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="text-center">
        <h1 className="text-6xl font-bold">404</h1>
        <h2 className="mt-2 text-xl font-semibold">Page Not Found</h2>
        <p className="text-muted-foreground mt-2">The page you are looking for does not exist.</p>
        <Button asChild variant="outline" className="mt-4">
          <Link href="/">Go Home</Link>
        </Button>
      </div>
    </div>
  );
}
