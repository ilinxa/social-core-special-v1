"use client";

import { Separator } from "@/components/ui/separator";
import { DangerZone } from "@/features/settings/components/DangerZone";
import { UsernameSection } from "@/features/settings/components/UsernameSection";
import { useUser } from "@/stores/auth-store";

export default function SettingsPage() {
  const user = useUser();

  if (!user) return null;

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">Settings</h1>

      <UsernameSection currentUsername={user.username} />

      <Separator />

      <DangerZone />
    </div>
  );
}
