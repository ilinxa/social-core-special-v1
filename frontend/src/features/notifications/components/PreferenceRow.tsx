"use client";

import React from "react";
import { Lock, RotateCcw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import type { PreferenceItem } from "@/features/notifications/types";

interface PreferenceRowProps {
  item: PreferenceItem;
  onToggle: (
    notificationType: string,
    channel: "email" | "push" | "sms",
    enabled: boolean,
  ) => void;
  onReset: (notificationType: string) => void;
}

export const PreferenceRow = React.memo(function PreferenceRow({
  item,
  onToggle,
  onReset,
}: PreferenceRowProps) {
  const disabled = !item.user_configurable;

  return (
    <div className="flex items-center justify-between gap-4 py-3">
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <p className="text-sm font-medium">{item.display_name}</p>
          {disabled && (
            <Lock className="h-3.5 w-3.5 text-muted-foreground" aria-label="Cannot be disabled" />
          )}
        </div>
        <p className="text-xs text-muted-foreground">{item.description}</p>
      </div>

      <div className="flex items-center gap-4">
        <label className="flex flex-col items-center gap-1">
          <Switch
            checked={item.email_enabled}
            onCheckedChange={(checked) =>
              onToggle(item.notification_type, "email", checked)
            }
            disabled={disabled}
            aria-label={`${item.display_name} email notifications`}
          />
          <span className="text-[10px] text-muted-foreground">Email</span>
        </label>

        <label className="flex flex-col items-center gap-1">
          <Switch
            checked={item.push_enabled}
            onCheckedChange={(checked) =>
              onToggle(item.notification_type, "push", checked)
            }
            disabled={disabled}
            aria-label={`${item.display_name} push notifications`}
          />
          <span className="text-[10px] text-muted-foreground">Push</span>
        </label>

        <label className="flex flex-col items-center gap-1">
          <Switch
            checked={item.sms_enabled}
            onCheckedChange={(checked) =>
              onToggle(item.notification_type, "sms", checked)
            }
            disabled={disabled}
            aria-label={`${item.display_name} SMS notifications`}
          />
          <span className="text-[10px] text-muted-foreground">SMS</span>
        </label>

        {!disabled && (
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            onClick={() => onReset(item.notification_type)}
            aria-label={`Reset ${item.display_name} to default`}
          >
            <RotateCcw className="h-3.5 w-3.5" />
          </Button>
        )}
      </div>
    </div>
  );
});
