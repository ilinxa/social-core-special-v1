"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2 } from "lucide-react";
import { useForm } from "react-hook-form";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { UsernameField } from "@/features/users/components/UsernameField";
import { useUpdateUsername } from "@/features/users/hooks/use-user-mutations";
import { handleApiError } from "@/lib/api-error-handler";
import { usernameSchema, type UsernameFormValues } from "@/lib/validations/profile";

interface UsernameSectionProps {
  currentUsername: string;
}

export function UsernameSection({ currentUsername }: UsernameSectionProps) {
  const updateUsername = useUpdateUsername();

  const {
    register,
    handleSubmit,
    setError,
    control,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<UsernameFormValues>({
    resolver: zodResolver(usernameSchema),
    defaultValues: { username: currentUsername },
  });

  const watchedUsername = watch("username");
  const hasChanged = watchedUsername !== currentUsername;

  async function onSubmit(values: UsernameFormValues) {
    if (!hasChanged) return;

    try {
      await updateUsername.mutateAsync({ username: values.username });
    } catch (error) {
      handleApiError<UsernameFormValues>(error, {
        setError,
        handlers: {
          conflict: () =>
            setError("username", { message: "Username is already taken" }),
          validation_error: (err) =>
            setError("username", {
              message: err.message || "Invalid username",
            }),
        },
      });
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Username</CardTitle>
        <CardDescription>
          Your unique identifier on the platform. 5-30 characters, letters, numbers, and
          underscores only.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
          <UsernameField
            control={control}
            currentUsername={currentUsername}
            error={errors.username}
            {...register("username")}
          />

          <div className="flex justify-end">
            <Button type="submit" disabled={isSubmitting || !hasChanged} size="sm">
              {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {isSubmitting ? "Saving..." : "Update Username"}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
