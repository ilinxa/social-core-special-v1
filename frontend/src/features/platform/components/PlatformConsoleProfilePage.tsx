"use client";

import { Can } from "@/components/common/Can";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  PlatformProfileSkeleton,
  PlatformProfileView,
} from "@/features/platform/components/PlatformProfileView";
import { PlatformProfileEditForm } from "@/features/platform/components/PlatformProfileEditForm";
import { usePlatformAccount } from "@/features/platform/hooks/use-platform-queries";

export function PlatformConsoleProfilePage() {
  const { data: account, isLoading } = usePlatformAccount();

  if (isLoading || !account) {
    return (
      <div className="mx-auto max-w-3xl space-y-6">
        <h1 className="text-2xl font-bold tracking-tight">Profile</h1>
        <PlatformProfileSkeleton />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">Profile</h1>
      <Can
        allowed={account._permissions.can_edit_profile}
        fallback={<PlatformProfileView account={account} />}
      >
        <Tabs defaultValue="edit">
          <TabsList>
            <TabsTrigger value="edit">Edit</TabsTrigger>
            <TabsTrigger value="preview">Preview</TabsTrigger>
          </TabsList>
          <TabsContent value="edit">
            <PlatformProfileEditForm account={account} />
          </TabsContent>
          <TabsContent value="preview">
            <PlatformProfileView account={account} />
          </TabsContent>
        </Tabs>
      </Can>
    </div>
  );
}
