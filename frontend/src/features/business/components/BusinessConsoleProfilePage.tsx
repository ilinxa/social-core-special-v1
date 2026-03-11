"use client";

import { useParams } from "next/navigation";

import { Can } from "@/components/common/Can";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  BusinessProfileSkeleton,
  BusinessProfileView,
} from "@/features/business/components/BusinessProfileView";
import { BusinessProfileEditForm } from "@/features/business/components/BusinessProfileEditForm";
import { useBusiness } from "@/features/business/hooks/use-business-queries";

export function BusinessConsoleProfilePage() {
  const { slug } = useParams<{ slug: string }>();
  const { data: business, isLoading } = useBusiness(slug);

  if (isLoading || !business) {
    return (
      <div className="mx-auto max-w-3xl space-y-6">
        <h1 className="text-2xl font-bold tracking-tight">Profile</h1>
        <BusinessProfileSkeleton />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">Profile</h1>
      <Can
        allowed={business._permissions.can_edit_profile}
        fallback={<BusinessProfileView business={business} />}
      >
        <Tabs defaultValue="edit">
          <TabsList>
            <TabsTrigger value="edit">Edit</TabsTrigger>
            <TabsTrigger value="preview">Preview</TabsTrigger>
          </TabsList>
          <TabsContent value="edit">
            <BusinessProfileEditForm business={business} />
          </TabsContent>
          <TabsContent value="preview">
            <BusinessProfileView business={business} />
          </TabsContent>
        </Tabs>
      </Can>
    </div>
  );
}
