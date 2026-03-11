"use client";

import { useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2 } from "lucide-react";
import { Controller, useForm } from "react-hook-form";
import { toast } from "sonner";

import { FormField } from "@/components/common/FormField";
import { FormTextarea } from "@/components/common/FormTextarea";
import { ImageUpload } from "@/components/common/ImageUpload";
import { SocialLinksEditor } from "@/components/common/SocialLinksEditor";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useUpdatePlatformProfile } from "@/features/platform/hooks/use-platform-mutations";
import { handleApiError } from "@/lib/api-error-handler";
import {
  platformProfileSchema,
  type PlatformProfileFormValues,
} from "@/lib/validations/platform-profile";
import type { PlatformAccountWithPerms } from "@/types/organization";

// =============================================================================
// PLATFORM PROFILE EDIT FORM
// =============================================================================

interface PlatformProfileEditFormProps {
  account: PlatformAccountWithPerms;
}

export function PlatformProfileEditForm({ account }: PlatformProfileEditFormProps) {
  const { profile } = account;
  const mutation = useUpdatePlatformProfile();

  // Image state (controlled, deferred upload)
  const [logoFile, setLogoFile] = useState<File | null>(null);
  const [faviconFile, setFaviconFile] = useState<File | null>(null);
  const [logoRemoved, setLogoRemoved] = useState(false);
  const [faviconRemoved, setFaviconRemoved] = useState(false);

  const {
    register,
    handleSubmit,
    setError,
    control,
    formState: { errors, isSubmitting },
  } = useForm<PlatformProfileFormValues>({
    resolver: zodResolver(platformProfileSchema),
    values: {
      name: profile.name,
      tagline: profile.tagline,
      description: profile.description,
      primary_color: profile.primary_color || "#000000",
      secondary_color: profile.secondary_color || "#000000",
      contact_email: profile.contact_email,
      contact_phone: profile.contact_phone,
      address: profile.address,
      social_links: profile.social_links,
    },
  });

  async function onSubmit(values: PlatformProfileFormValues) {
    // Build payload with only changed fields
    const payload: Record<string, unknown> = {};

    if (values.name !== profile.name) payload.name = values.name;
    if (values.tagline !== profile.tagline) payload.tagline = values.tagline;
    if (values.description !== profile.description) payload.description = values.description;
    if (values.primary_color !== profile.primary_color) payload.primary_color = values.primary_color;
    if (values.secondary_color !== profile.secondary_color) payload.secondary_color = values.secondary_color;
    if (values.contact_email !== profile.contact_email) payload.contact_email = values.contact_email;
    if (values.contact_phone !== profile.contact_phone) payload.contact_phone = values.contact_phone;
    if (values.address !== profile.address) payload.address = values.address;
    if (JSON.stringify(values.social_links) !== JSON.stringify(profile.social_links)) {
      payload.social_links = values.social_links;
    }

    // Image changes
    if (logoFile) payload.logo = logoFile;
    else if (logoRemoved) payload.logo = null;
    if (faviconFile) payload.favicon = faviconFile;
    else if (faviconRemoved) payload.favicon = null;

    if (Object.keys(payload).length === 0) {
      toast.info("No changes to save");
      return;
    }

    try {
      await mutation.mutateAsync(payload);
      toast.success("Profile updated");
      setLogoFile(null);
      setFaviconFile(null);
      setLogoRemoved(false);
      setFaviconRemoved(false);
    } catch (error) {
      handleApiError<PlatformProfileFormValues>(error, { setError });
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6" noValidate>
      {errors.root && (
        <div role="alert" className="bg-destructive/10 text-destructive flex items-center gap-2 rounded-lg px-4 py-3 text-sm">
          {errors.root.message}
        </div>
      )}

      {/* Images */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Images</CardTitle>
          <CardDescription>Your logo and favicon represent your platform.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <ImageUpload
            currentUrl={logoRemoved ? null : profile.logo}
            value={logoFile}
            onChange={(file) => {
              setLogoFile(file);
              setLogoRemoved(file === null && !profile.logo ? false : file === null);
            }}
            label="Logo"
            aspectHint="1:1"
            shape="square"
          />
          <ImageUpload
            currentUrl={faviconRemoved ? null : profile.favicon}
            value={faviconFile}
            onChange={(file) => {
              setFaviconFile(file);
              setFaviconRemoved(file === null && !profile.favicon ? false : file === null);
            }}
            label="Favicon"
            aspectHint="1:1 (small)"
            shape="square"
          />
        </CardContent>
      </Card>

      {/* Basic Info */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Basic Information</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <FormField
            label="Name"
            placeholder="Platform name"
            error={errors.name}
            {...register("name")}
          />
          <FormField
            label="Tagline"
            placeholder="A short description"
            error={errors.tagline}
            {...register("tagline")}
          />
          <FormTextarea
            label="Description"
            placeholder="Tell people about this platform..."
            error={errors.description}
            rows={4}
            {...register("description")}
          />
        </CardContent>
      </Card>

      {/* Branding */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Branding</CardTitle>
          <CardDescription>Define your platform&apos;s brand colors.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Controller
            control={control}
            name="primary_color"
            render={({ field }) => (
              <div className="space-y-2">
                <Label htmlFor="primary_color">Primary color</Label>
                <div className="flex items-center gap-3">
                  <Input
                    type="color"
                    id="primary_color"
                    value={field.value}
                    onChange={field.onChange}
                    className="h-10 w-14 cursor-pointer p-1"
                  />
                  <Input
                    value={field.value}
                    onChange={field.onChange}
                    placeholder="#000000"
                    className="w-32 font-mono"
                  />
                </div>
                {errors.primary_color && (
                  <p className="text-destructive text-sm">{errors.primary_color.message}</p>
                )}
              </div>
            )}
          />

          <Controller
            control={control}
            name="secondary_color"
            render={({ field }) => (
              <div className="space-y-2">
                <Label htmlFor="secondary_color">Secondary color</Label>
                <div className="flex items-center gap-3">
                  <Input
                    type="color"
                    id="secondary_color"
                    value={field.value}
                    onChange={field.onChange}
                    className="h-10 w-14 cursor-pointer p-1"
                  />
                  <Input
                    value={field.value}
                    onChange={field.onChange}
                    placeholder="#000000"
                    className="w-32 font-mono"
                  />
                </div>
                {errors.secondary_color && (
                  <p className="text-destructive text-sm">{errors.secondary_color.message}</p>
                )}
              </div>
            )}
          />
        </CardContent>
      </Card>

      {/* Contact */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Contact Information</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <FormField
            label="Contact email"
            type="email"
            placeholder="contact@platform.com"
            error={errors.contact_email}
            {...register("contact_email")}
          />
          <FormField
            label="Contact phone"
            type="tel"
            placeholder="+1 (555) 000-0000"
            error={errors.contact_phone}
            {...register("contact_phone")}
          />
          <FormTextarea
            label="Address"
            placeholder="Street address, city, state, country"
            error={errors.address}
            rows={2}
            {...register("address")}
          />
        </CardContent>
      </Card>

      {/* Social Links */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Social Links</CardTitle>
        </CardHeader>
        <CardContent>
          <Controller
            control={control}
            name="social_links"
            render={({ field }) => (
              <SocialLinksEditor value={field.value} onChange={field.onChange} />
            )}
          />
        </CardContent>
      </Card>

      {/* Actions */}
      <div className="flex items-center justify-end gap-3">
        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          {isSubmitting ? "Saving..." : "Save Changes"}
        </Button>
      </div>
    </form>
  );
}
