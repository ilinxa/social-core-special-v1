"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Lock, Timer } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  clearGovernanceToken,
  getGovernanceTimeRemaining,
} from "@/lib/governance-token";

/**
 * Governance session timer + Lock Console button.
 *
 * Shows remaining time on the governance token and allows
 * the user to manually lock the console (clear token + redirect).
 * Updates every second for accurate countdown.
 */
export function GovernanceSessionBar() {
  const router = useRouter();
  const [remaining, setRemaining] = useState(() =>
    getGovernanceTimeRemaining(),
  );

  useEffect(() => {
    const interval = setInterval(() => {
      const secs = getGovernanceTimeRemaining();
      setRemaining(secs);

      if (secs <= 0) {
        clearInterval(interval);
        clearGovernanceToken();
        router.replace("/gconsole/authenticate");
      }
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  const handleLock = useCallback(() => {
    clearGovernanceToken();
    router.replace("/gconsole/authenticate");
  }, [router]);

  const minutes = Math.floor(remaining / 60);
  const seconds = remaining % 60;
  const isLow = remaining > 0 && remaining <= 120;

  return (
    <div className="rounded-lg border p-3">
      <div className="mb-2 flex items-center gap-2">
        <Timer
          className={`h-4 w-4 ${isLow ? "text-amber-500" : "text-muted-foreground"}`}
        />
        <span
          className={`text-sm font-medium tabular-nums ${isLow ? "text-amber-500" : ""}`}
        >
          {remaining > 0
            ? `${minutes}:${seconds.toString().padStart(2, "0")}`
            : "Expired"}
        </span>
        <span className="text-muted-foreground text-xs">remaining</span>
      </div>
      <Button
        variant="outline"
        size="sm"
        className="w-full"
        onClick={handleLock}
      >
        <Lock className="mr-2 h-3.5 w-3.5" />
        Lock Console
      </Button>
    </div>
  );
}
