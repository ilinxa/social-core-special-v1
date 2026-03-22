"use client";

import { useState } from "react";
import { AlertTriangle, Loader2 } from "lucide-react";
import { useRouter } from "next/navigation";

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
import { useDeactivateAccount } from "@/features/users/hooks/use-user-mutations";

export function DangerZone() {
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
