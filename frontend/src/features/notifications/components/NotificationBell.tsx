"use client";

import { Bell } from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { NotificationDropdown } from "@/features/notifications/components/NotificationDropdown";
import { useNotificationScopes } from "@/features/notifications/hooks/use-notification-queries";
import {
  useNotificationDropdownOpen,
  useNotificationStore,
  useNotificationSystemEnabled,
  useNotificationTotalUnread,
} from "@/stores/notification-store";

export function NotificationBell() {
  // Probe feature gate — this query detects SG off (404)
  useNotificationScopes();

  const isSystemEnabled = useNotificationSystemEnabled();
  const totalUnread = useNotificationTotalUnread();
  const dropdownOpen = useNotificationDropdownOpen();
  const setDropdownOpen = useNotificationStore((s) => s.setDropdownOpen);

  // Don't render when system is disabled
  if (!isSystemEnabled) return null;

  const badgeText = totalUnread > 99 ? "99+" : String(totalUnread);

  return (
    <>
      {/* Desktop: Popover dropdown */}
      <div className="hidden md:block">
        <Popover open={dropdownOpen} onOpenChange={setDropdownOpen}>
          <PopoverTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className="relative"
              aria-label="Notifications"
              aria-haspopup="dialog"
            >
              <Bell className="h-5 w-5" />
              {totalUnread > 0 && (
                <Badge
                  variant="destructive"
                  className="absolute -right-1 -top-1 h-5 min-w-5 px-1 text-[10px]"
                >
                  {badgeText}
                </Badge>
              )}
            </Button>
          </PopoverTrigger>
          <PopoverContent align="end" className="w-80 p-0">
            <NotificationDropdown />
          </PopoverContent>
        </Popover>
      </div>

      {/* Mobile: Direct link */}
      <div className="md:hidden">
        <Button
          variant="ghost"
          size="icon"
          className="relative"
          aria-label="Notifications"
          asChild
        >
          <Link href="/notifications">
            <Bell className="h-5 w-5" />
            {totalUnread > 0 && (
              <Badge
                variant="destructive"
                className="absolute -right-1 -top-1 h-5 min-w-5 px-1 text-[10px]"
              >
                {badgeText}
              </Badge>
            )}
          </Link>
        </Button>
      </div>
    </>
  );
}
