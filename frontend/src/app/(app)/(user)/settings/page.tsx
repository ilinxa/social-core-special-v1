"use client";

import { useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { AlertTriangle, Loader2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { UsernameField } from "@/features/users/components/UsernameField";
import { useUpdateUsername, useDeactivateAccount } from "@/features/users/hooks/use-user-mutations";
import { handleApiError } from "@/lib/api-error-handler";
import { usernameSchema, type UsernameFormValues } from "@/lib/validations/profile";
import { useUser } from "@/stores/auth-store";

// =============================================================================
// SETTINGS PAGE
// =============================================================================

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

// =============================================================================
// USERNAME SECTION
// =============================================================================

function UsernameSection({ currentUsername }: { currentUsername: string }) {
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
              message: err.error?.message || "Invalid username",
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

// =============================================================================
// DANGER ZONE
// =============================================================================

function DangerZone() {
  const [confirmText, setConfirmText] = useState("");
  const [open, setOpen] = useState(false);
  const router = useRouter();
  const deactivate = useDeactivateAccount();

  async function handleDeactivate() {
    try {
      await deactivate.mutateAsync();
      router.push("/login");
    } catch {
      // Error handled by mutation (toast)
    }
  }

  return (
    <Card className="border-destructive/50">
      <CardHeader>
        <CardTitle className="text-destructive text-base">Danger Zone</CardTitle>
        <CardDescription>
          Irreversible actions that affect your account.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <p className="text-sm font-medium">Deactivate account</p>
            <p className="text-muted-foreground text-sm">
              Your profile will be hidden and you will be logged out.
            </p>
          </div>

          <AlertDialog open={open} onOpenChange={setOpen}>
            <AlertDialogTrigger asChild>
              <Button variant="destructive" size="sm">
                Deactivate
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle className="flex items-center gap-2">
                  <AlertTriangle className="text-destructive h-5 w-5" />
                  Deactivate your account?
                </AlertDialogTitle>
                <AlertDialogDescription className="space-y-2">
                  <span className="block">
                    This will deactivate your account. Your profile will be hidden from
                    other users and you will be logged out of all sessions.
                  </span>
                  <span className="block">
                    To confirm, type <strong>deactivate</strong> below.
                  </span>
                </AlertDialogDescription>
              </AlertDialogHeader>

              <Input
                placeholder="Type 'deactivate' to confirm"
                value={confirmText}
                onChange={(e) => setConfirmText(e.target.value)}
                autoComplete="off"
              />

              <AlertDialogFooter>
                <AlertDialogCancel onClick={() => setConfirmText("")}>
                  Cancel
                </AlertDialogCancel>
                <AlertDialogAction
                  disabled={confirmText !== "deactivate" || deactivate.isPending}
                  onClick={handleDeactivate}
                  className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                >
                  {deactivate.isPending ? "Deactivating..." : "Deactivate Account"}
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </CardContent>
    </Card>
  );
}
