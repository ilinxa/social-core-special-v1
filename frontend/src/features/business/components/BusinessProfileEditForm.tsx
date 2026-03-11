"use client";

import { useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2 } from "lucide-react";
import { Controller, useForm } from "react-hook-form";
import { toast } from "sonner";

import { ComboboxField } from "@/components/common/ComboboxField";
import { FormField } from "@/components/common/FormField";
import { FormTagInput } from "@/components/common/FormTagInput";
import { FormTextarea } from "@/components/common/FormTextarea";
import { ImageUpload } from "@/components/common/ImageUpload";
import { SocialLinksEditor } from "@/components/common/SocialLinksEditor";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { COUNTRY_NAMES } from "@/lib/country-data";
import { useCitiesForCountry } from "@/hooks/use-city-data";
import { useUpdateBusiness, useUpdateBusinessProfile } from "@/features/business/hooks/use-business-mutations";
import { handleApiError } from "@/lib/api-error-handler";
import {
  businessProfileSchema,
  COMPANY_SIZE_OPTIONS,
  type BusinessProfileFormValues,
} from "@/lib/validations/business-profile";
import type { BusinessAccountWithPerms } from "@/types/organization";

// =============================================================================
// BUSINESS PROFILE EDIT FORM
// =============================================================================

interface BusinessProfileEditFormProps {
  business: BusinessAccountWithPerms;
}

export function BusinessProfileEditForm({ business }: BusinessProfileEditFormProps) {
  const { profile } = business;
  const profileMutation = useUpdateBusinessProfile(business.slug);
  const accountMutation = useUpdateBusiness(business.slug);

  // City options for the business's country
  const cityNames = useCitiesForCountry(business.country);
  const cityOptions = cityNames.map((c) => ({ value: c, label: c }));

  // Image state (controlled, deferred upload)
  const [logoFile, setLogoFile] = useState<File | null>(null);
  const [coverFile, setCoverFile] = useState<File | null>(null);
  const [logoRemoved, setLogoRemoved] = useState(false);
  const [coverRemoved, setCoverRemoved] = useState(false);

  const {
    register,
    handleSubmit,
    setError,
    control,
    formState: { errors, isSubmitting },
  } = useForm<BusinessProfileFormValues>({
    resolver: zodResolver(businessProfileSchema),
    values: {
      display_name: profile.display_name,
      tagline: profile.tagline,
      description: profile.description,
      website: profile.website,
      contact_email: profile.contact_email,
      contact_phone: profile.contact_phone,
      industry: profile.industry,
      company_size: profile.company_size,
      founded_year: profile.founded_year,
      social_links: profile.social_links,
      tags: profile.tags,
      is_public: profile.is_public,
      city: business.city,
    },
  });

  async function onSubmit(values: BusinessProfileFormValues) {
    // Build profile payload with only changed fields
    const profilePayload: Record<string, unknown> = {};

    if (values.display_name !== profile.display_name) profilePayload.display_name = values.display_name;
    if (values.tagline !== profile.tagline) profilePayload.tagline = values.tagline;
    if (values.description !== profile.description) profilePayload.description = values.description;
    if (values.website !== profile.website) profilePayload.website = values.website;
    if (values.contact_email !== profile.contact_email) profilePayload.contact_email = values.contact_email;
    if (values.contact_phone !== profile.contact_phone) profilePayload.contact_phone = values.contact_phone;
    if (values.industry !== profile.industry) profilePayload.industry = values.industry;
    if (values.company_size !== profile.company_size) profilePayload.company_size = values.company_size;
    if (values.founded_year !== profile.founded_year) profilePayload.founded_year = values.founded_year;
    if (values.is_public !== profile.is_public) profilePayload.is_public = values.is_public;
    if (JSON.stringify(values.social_links) !== JSON.stringify(profile.social_links)) {
      profilePayload.social_links = values.social_links;
    }
    if (JSON.stringify(values.tags) !== JSON.stringify(profile.tags)) {
      profilePayload.tags = values.tags;
    }

    // Image changes
    if (logoFile) profilePayload.logo = logoFile;
    else if (logoRemoved) profilePayload.logo = null;
    if (coverFile) profilePayload.cover_image = coverFile;
    else if (coverRemoved) profilePayload.cover_image = null;

    // Build account payload (city is account-level)
    const accountPayload: Record<string, unknown> = {};
    if (values.city !== business.city) accountPayload.city = values.city;

    const hasProfileChanges = Object.keys(profilePayload).length > 0;
    const hasAccountChanges = Object.keys(accountPayload).length > 0;

    if (!hasProfileChanges && !hasAccountChanges) {
      toast.info("No changes to save");
      return;
    }

    try {
      const promises: Promise<unknown>[] = [];
      if (hasProfileChanges) promises.push(profileMutation.mutateAsync(profilePayload));
      if (hasAccountChanges) promises.push(accountMutation.mutateAsync(accountPayload));
      await Promise.all(promises);
      toast.success("Profile updated");
      // Reset image state after successful save
      setLogoFile(null);
      setCoverFile(null);
      setLogoRemoved(false);
      setCoverRemoved(false);
    } catch (error) {
      handleApiError<BusinessProfileFormValues>(error, { setError });
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
          <CardDescription>Your logo and cover image appear on your business profile.</CardDescription>
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
            currentUrl={coverRemoved ? null : profile.cover_image}
            value={coverFile}
            onChange={(file) => {
              setCoverFile(file);
              setCoverRemoved(file === null && !profile.cover_image ? false : file === null);
            }}
            label="Cover Image"
            aspectHint="16:9"
            shape="wide"
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
            label="Display name"
            placeholder="Your business display name"
            error={errors.display_name}
            {...register("display_name")}
          />
          <FormField
            label="Tagline"
            placeholder="A short description of your business"
            error={errors.tagline}
            {...register("tagline")}
          />
          <FormTextarea
            label="Description"
            placeholder="Tell people about your business..."
            error={errors.description}
            rows={4}
            {...register("description")}
          />
        </CardContent>
      </Card>

      {/* Visibility */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Visibility</CardTitle>
          <CardDescription>Control who can see your business profile.</CardDescription>
        </CardHeader>
        <CardContent>
          <Controller
            control={control}
            name="is_public"
            render={({ field }) => (
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label htmlFor="is_public">Public profile</Label>
                  <p className="text-muted-foreground text-sm">
                    When enabled, anyone can view your business profile.
                  </p>
                </div>
                <Switch
                  id="is_public"
                  checked={field.value}
                  onCheckedChange={field.onChange}
                />
              </div>
            )}
          />
        </CardContent>
      </Card>

      {/* Business Details */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Business Details</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <FormField
            label="Industry"
            placeholder="e.g., Technology, Healthcare"
            error={errors.industry}
            {...register("industry")}
          />

          <Controller
            control={control}
            name="company_size"
            render={({ field }) => (
              <ComboboxField
                label="Company size"
                value={field.value}
                onChange={field.onChange}
                options={COMPANY_SIZE_OPTIONS}
                searchPlaceholder="Search size..."
                emptyText="No option found."
                error={errors.company_size?.message}
              />
            )}
          />

          <FormField
            label="Founded year"
            type="number"
            placeholder="e.g., 2020"
            error={errors.founded_year}
            {...register("founded_year", { setValueAs: (v) => (v === "" ? null : Number(v)) })}
          />
        </CardContent>
      </Card>

      {/* Location */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Location</CardTitle>
          <CardDescription>Where your business is located.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-1">
            <Label className="text-muted-foreground text-sm">Country</Label>
            <p className="text-sm font-medium">{COUNTRY_NAMES[business.country] ?? business.country}</p>
          </div>
          <Controller
            control={control}
            name="city"
            render={({ field }) => (
              <ComboboxField
                label="City"
                value={field.value}
                onChange={field.onChange}
                options={cityOptions}
                searchPlaceholder="Search city..."
                emptyText="No city found."
                error={errors.city?.message}
              />
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
            label="Website"
            type="url"
            placeholder="https://example.com"
            error={errors.website}
            {...register("website")}
          />
          <FormField
            label="Contact email"
            type="email"
            placeholder="contact@example.com"
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
        </CardContent>
      </Card>

      {/* Tags */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Tags</CardTitle>
          <CardDescription>Add tags to help people discover your business.</CardDescription>
        </CardHeader>
        <CardContent>
          <Controller
            control={control}
            name="tags"
            render={({ field }) => (
              <FormTagInput
                label="Tags"
                value={field.value}
                onChange={field.onChange}
                category="business"
                error={errors.tags?.message}
              />
            )}
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
