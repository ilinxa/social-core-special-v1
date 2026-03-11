"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { CountrySelect } from "@/features/explore/components/CountrySelect";
import { useCreateBusiness } from "@/features/business/hooks/use-business-mutations";
import {
  createBusinessSchema,
  BUSINESS_TYPE_OPTIONS,
  type CreateBusinessFormValues,
} from "@/lib/validations/create-business";

interface CreateBusinessDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: (slug: string) => void;
}

export function CreateBusinessDialog({
  open,
  onOpenChange,
  onSuccess,
}: CreateBusinessDialogProps) {
  const createBusiness = useCreateBusiness();

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    reset,
    formState: { errors },
  } = useForm<CreateBusinessFormValues>({
    resolver: zodResolver(createBusinessSchema),
    defaultValues: {
      legal_name: "",
      country: "",
      slug: "",
      business_type: "",
      display_name: "",
    },
  });

  const countryValue = watch("country");

  function handleClose() {
    reset();
    onOpenChange(false);
  }

  function onSubmit(data: CreateBusinessFormValues) {
    const payload: Parameters<typeof createBusiness.mutate>[0] = {
      legal_name: data.legal_name,
      country: data.country,
    };
    if (data.slug) payload.slug = data.slug;
    if (data.business_type) payload.business_type = data.business_type;
    if (data.display_name) payload.display_name = data.display_name;

    createBusiness.mutate(payload, {
      onSuccess: (result) => {
        handleClose();
        onSuccess(result.slug);
      },
    });
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Create Business Account</DialogTitle>
          <DialogDescription>
            Set up a new business account. You can customize its profile later.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {/* Legal Name */}
          <div className="space-y-2">
            <Label htmlFor="legal_name">Legal Name *</Label>
            <Input
              id="legal_name"
              placeholder="Your business legal name"
              {...register("legal_name")}
            />
            {errors.legal_name && (
              <p className="text-sm text-destructive">{errors.legal_name.message}</p>
            )}
          </div>

          {/* Country */}
          <div className="space-y-2">
            <Label>Country *</Label>
            <CountrySelect
              value={countryValue}
              onChange={(val) => setValue("country", val, { shouldValidate: true })}
            />
            {errors.country && (
              <p className="text-sm text-destructive">{errors.country.message}</p>
            )}
          </div>

          {/* Display Name */}
          <div className="space-y-2">
            <Label htmlFor="display_name">Display Name</Label>
            <Input
              id="display_name"
              placeholder="Public-facing name (optional)"
              {...register("display_name")}
            />
            {errors.display_name && (
              <p className="text-sm text-destructive">{errors.display_name.message}</p>
            )}
          </div>

          {/* Slug */}
          <div className="space-y-2">
            <Label htmlFor="slug">URL Slug</Label>
            <Input
              id="slug"
              placeholder="my-business (auto-generated if blank)"
              {...register("slug")}
            />
            {errors.slug && (
              <p className="text-sm text-destructive">{errors.slug.message}</p>
            )}
          </div>

          {/* Business Type */}
          <div className="space-y-2">
            <Label>Business Type</Label>
            <Select
              value={watch("business_type") ?? ""}
              onValueChange={(val) => setValue("business_type", val)}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select type..." />
              </SelectTrigger>
              <SelectContent>
                {BUSINESS_TYPE_OPTIONS.filter((o) => o.value !== "").map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* API Error */}
          {createBusiness.isError && (
            <p className="text-sm text-destructive">
              {createBusiness.error?.message || "Failed to create business. Please try again."}
            </p>
          )}

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={handleClose}
              disabled={createBusiness.isPending}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={createBusiness.isPending}>
              {createBusiness.isPending ? "Creating..." : "Create Business"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
