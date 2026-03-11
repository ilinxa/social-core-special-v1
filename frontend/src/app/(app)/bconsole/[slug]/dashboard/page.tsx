"use client";

import { useParams } from "next/navigation";

export default function BusinessDashboardPage() {
  const { slug } = useParams<{ slug: string }>();

  return (
    <div className="space-y-4">
      <h1 className="text-3xl font-bold">Business Dashboard</h1>
      <p className="text-muted-foreground">Managing: {slug}</p>
    </div>
  );
}
