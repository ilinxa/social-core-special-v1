"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Bell,
  Building2,
  Compass,
  FileText,
  Home,
  LayoutDashboard,
  Menu,
  Newspaper,
  Settings,
  User,
  Users,
} from "lucide-react";

import { MobileMenuSheet } from "@/components/navigation/MobileMenuSheet";
import { useNavContext } from "@/hooks/use-nav-context";
import { isNavActive } from "@/lib/navigation-config";
import { cn } from "@/lib/utils";
import type { NavContext } from "@/types/navigation";

interface BottomNavItem {
  key: string;
  label: string;
  icon: React.ElementType;
  href: string;
}

function getBottomNavItems(context: NavContext): BottomNavItem[] {
  switch (context.type) {
    case "personal":
      return [
        { key: "home", label: "Home", icon: Home, href: "/home" },
        { key: "explore", label: "Explore", icon: Compass, href: "/explore" },
        { key: "notif", label: "Alerts", icon: Bell, href: "/notifications" },
        { key: "profile", label: "Profile", icon: User, href: "/profile" },
      ];
    case "business":
      return [
        { key: "dash", label: "Dashboard", icon: LayoutDashboard, href: `/bconsole/${context.slug}/dashboard` },
        { key: "members", label: "Members", icon: Users, href: `/bconsole/${context.slug}/members` },
        { key: "forms", label: "Forms", icon: FileText, href: `/bconsole/${context.slug}/forms` },
        { key: "settings", label: "Settings", icon: Settings, href: `/bconsole/${context.slug}/settings` },
      ];
    case "platform":
      return [
        { key: "dash", label: "Dashboard", icon: LayoutDashboard, href: "/pconsole/dashboard" },
        { key: "biz", label: "Businesses", icon: Building2, href: "/pconsole/businesses" },
        { key: "members", label: "Members", icon: Users, href: "/pconsole/members" },
        { key: "cms", label: "CMS", icon: Newspaper, href: "/pconsole/cms/sites" },
      ];
  }
}

export function BottomNavbar() {
  const [menuOpen, setMenuOpen] = useState(false);
  const context = useNavContext();
  const pathname = usePathname();
  const items = getBottomNavItems(context);

  return (
    <nav aria-label="Mobile navigation" className="fixed bottom-0 left-0 right-0  z-40 border-t border-border bg-background md:hidden">
      <div className="flex h-14  items-center justify-around px-2">
        
        {items.map((item) => {
          const Icon = item.icon;
          const active = isNavActive(pathname, item.href, "prefix");
          return (
            <Link
              key={item.key}
              href={item.href}
              className={cn(
                "flex flex-col items-center justify-center gap-0.5 px-2 py-1 text-[10px] transition-colors",
                active ? "text-primary" : "text-muted-foreground",
              )}
            >
              <Icon className="h-5 w-5" />
              {item.label}
            </Link>
          );
        })}
        <MobileMenuSheet open={menuOpen} onOpenChange={setMenuOpen}>
          <button
            className="flex flex-col items-center justify-center gap-0.5 px-2 py-1 text-[10px] text-muted-foreground transition-colors"
          >
            <Menu className="h-5 w-5 " />
            More
          </button>
        </MobileMenuSheet>
      </div>
      {/* iOS safe area */}
      <div className="h-[env(safe-area-inset-bottom)]" />
    </nav>
  );
}
