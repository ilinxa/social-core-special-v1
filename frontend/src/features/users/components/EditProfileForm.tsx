"use client";

import { useMemo } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowLeft, Globe, Languages, Loader2, MapPin } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Controller, useForm } from "react-hook-form";
import { toast } from "sonner";

import { ComboboxField } from "@/components/common/ComboboxField";
import { FormField } from "@/components/common/FormField";
import { FormTagInput } from "@/components/common/FormTagInput";
import { FormTextarea } from "@/components/common/FormTextarea";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import { COUNTRY_OPTIONS } from "@/lib/country-data";
import { useCitiesForCountry } from "@/hooks/use-city-data";
import { AvatarUpload } from "@/features/users/components/AvatarUpload";
import { CoverImageUpload } from "@/features/users/components/CoverImageUpload";
import { useUpdateProfile } from "@/features/users/hooks/use-user-mutations";
import { useProfile } from "@/features/users/hooks/use-user-queries";
import { handleApiError } from "@/lib/api-error-handler";
import { editProfileSchema, type EditProfileFormValues } from "@/lib/validations/profile";
import { useUser } from "@/stores/auth-store";

// =============================================================================
// CONSTANTS
// =============================================================================

const LANGUAGES = [
  { value: "en", label: "English" },
  { value: "es", label: "Spanish" },
  { value: "fr", label: "French" },
  { value: "de", label: "German" },
  { value: "ar", label: "Arabic" },
  { value: "zh", label: "Chinese" },
  { value: "ja", label: "Japanese" },
  { value: "ko", label: "Korean" },
  { value: "pt", label: "Portuguese" },
  { value: "ru", label: "Russian" },
] as const;

// =============================================================================
// LOADING SKELETON
// =============================================================================

function EditProfileSkeleton() {
  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div className="flex items-center gap-3">
        <Skeleton className="h-9 w-9 rounded-md" />
        <Skeleton className="h-8 w-40" />
      </div>
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center gap-5">
            <Skeleton className="h-24 w-24 rounded-full" />
            <div className="space-y-2">
              <Skeleton className="h-8 w-28" />
              <Skeleton className="h-8 w-20" />
            </div>
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="space-y-4 pt-6">
          <div className="grid gap-4 sm:grid-cols-2">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
          </div>
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-20 w-full" />
          <div className="grid gap-4 sm:grid-cols-2">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
          </div>
          <Skeleton className="h-10 w-full" />
        </CardContent>
      </Card>
    </div>
  );
}

// =============================================================================
// EDIT PROFILE FORM
// =============================================================================

function getInitials(displayName: string, email: string): string {
  if (displayName && displayName !== email) return displayName[0].toUpperCase();
  return email[0]?.toUpperCase() ?? "?";
}

export function EditProfileForm() {
  const user = useUser();
  const { data: profile, isLoading } = useProfile();
  const router = useRouter();
  const updateProfile = useUpdateProfile();

  const timezoneOptions = useMemo(
    () =>
      Intl.supportedValuesOf("timeZone").map((tz) => ({
        value: tz,
        label: tz.replace(/_/g, " "),
      })),
    [],
  );

  const {
    register,
    handleSubmit,
    setError,
    control,
    watch,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<EditProfileFormValues>({
    resolver: zodResolver(editProfileSchema),
    values: profile
      ? {
          first_name: profile.first_name,
          last_name: profile.last_name,
          phone: profile.phone,
          bio: profile.bio,
          timezone: profile.timezone,
          language: profile.language,
          country: profile.country,
          city: profile.city,
          tags: profile.tags ?? [],
          is_public: profile.is_public,
        }
      : undefined,
  });

  const selectedCountry = watch("country");
  const cities = useCitiesForCountry(selectedCountry ?? "");

  const cityOptions = useMemo(
    () => cities.map((c) => ({ value: c, label: c })),
    [cities],
  );

  if (isLoading || !user || !profile) {
    return <EditProfileSkeleton />;
  }

  async function onSubmit(values: EditProfileFormValues) {
    const profileChanged =
      values.first_name !== profile!.first_name ||
      values.last_name !== profile!.last_name ||
      values.phone !== profile!.phone ||
      values.bio !== profile!.bio ||
      values.timezone !== profile!.timezone ||
      values.language !== profile!.language ||
      values.country !== profile!.country ||
      values.city !== profile!.city ||
      JSON.stringify(values.tags) !== JSON.stringify(profile!.tags) ||
      values.is_public !== profile!.is_public;

    if (!profileChanged) {
      toast.info("No changes to save");
      return;
    }

    try {
      await updateProfile.mutateAsync({
        first_name: values.first_name,
        last_name: values.last_name,
        phone: values.phone,
        bio: values.bio,
        timezone: values.timezone,
        language: values.language,
        country: values.country,
        city: values.city,
        tags: values.tags,
        is_public: values.is_public,
      });
      toast.success("Profile updated");
      router.push("/profile");
    } catch (error) {
      handleApiError<EditProfileFormValues>(error, { setError });
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      {/* Page header */}
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="icon" asChild>
          <Link href="/profile" aria-label="Back to profile">
            <ArrowLeft className="h-4 w-4" />
          </Link>
        </Button>
        <h1 className="text-2xl font-bold tracking-tight">Edit Profile</h1>
      </div>

      {/* Photo section */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Photo</CardTitle>
          <CardDescription>
            Your photo appears on your profile and across the platform.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <AvatarUpload
            avatarUrl={profile.avatar_url}
            hasAvatar={profile.has_avatar}
            fallbackText={getInitials(profile.display_name, user.email)}
          />
          <Separator />
          <CoverImageUpload
            coverImageUrl={profile.cover_image_url}
            hasCoverImage={profile.has_cover_image}
          />
        </CardContent>
      </Card>

      {/* Form section */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Profile Information</CardTitle>
          <CardDescription>
            Update your personal details. Changes are saved when you click Save.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-5" noValidate>
            {errors.root && (
              <div role="alert" className="bg-destructive/10 text-destructive flex items-center gap-2 rounded-lg px-4 py-3 text-sm">
                {errors.root.message}
              </div>
            )}

            <div className="grid gap-4 sm:grid-cols-2">
              <FormField
                label="First name"
                placeholder="Enter first name"
                error={errors.first_name}
                {...register("first_name")}
              />
              <FormField
                label="Last name"
                placeholder="Enter last name"
                error={errors.last_name}
                {...register("last_name")}
              />
            </div>

            <FormField
              label="Phone"
              type="tel"
              placeholder="+1 (555) 000-0000"
              error={errors.phone}
              {...register("phone")}
            />

            <FormTextarea
              label="Bio"
              placeholder="Tell people about yourself..."
              error={errors.bio}
              rows={3}
              {...register("bio")}
            />

            <Separator />

            {/* Location */}
            <div className="grid gap-4 sm:grid-cols-2">
              <Controller
                control={control}
                name="country"
                render={({ field }) => (
                  <ComboboxField
                    label="Country"
                    value={field.value}
                    onChange={(v) => {
                      field.onChange(v);
                      if (v !== selectedCountry) {
                        setValue("city", "");
                      }
                    }}
                    options={COUNTRY_OPTIONS}
                    searchPlaceholder="Search country..."
                    emptyText="No country found."
                    error={errors.country?.message}
                    icon={MapPin}
                  />
                )}
              />

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
                    emptyText={selectedCountry ? "No city found." : "Select a country first."}
                    error={errors.city?.message}
                    disabled={!selectedCountry}
                  />
                )}
              />
            </div>

            <Separator />

            {/* Timezone + Language */}
            <div className="grid gap-4 sm:grid-cols-2">
              <Controller
                control={control}
                name="timezone"
                render={({ field }) => (
                  <ComboboxField
                    label="Timezone"
                    value={field.value}
                    onChange={field.onChange}
                    options={timezoneOptions}
                    searchPlaceholder="Search timezone..."
                    emptyText="No timezone found."
                    error={errors.timezone?.message}
                    icon={Globe}
                  />
                )}
              />

              <Controller
                control={control}
                name="language"
                render={({ field }) => (
                  <ComboboxField
                    label="Language"
                    value={field.value}
                    onChange={field.onChange}
                    options={LANGUAGES}
                    searchPlaceholder="Search language..."
                    emptyText="No language found."
                    error={errors.language?.message}
                    icon={Languages}
                  />
                )}
              />
            </div>

            <Separator />

            {/* Tags */}
            <Controller
              control={control}
              name="tags"
              render={({ field }) => (
                <FormTagInput
                  label="Tags"
                  value={field.value}
                  onChange={field.onChange}
                  category="user"
                  error={errors.tags?.message}
                />
              )}
            />

            <Separator />

            {/* Visibility */}
            <Controller
              control={control}
              name="is_public"
              render={({ field }) => (
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label htmlFor="is_public">Public profile</Label>
                    <p className="text-muted-foreground text-sm">
                      When enabled, other users can find and view your profile.
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

            <Separator />

            {/* Actions */}
            <div className="flex items-center justify-end gap-3">
              <Button variant="outline" asChild>
                <Link href="/profile">Cancel</Link>
              </Button>
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                {isSubmitting ? "Saving..." : "Save Changes"}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
