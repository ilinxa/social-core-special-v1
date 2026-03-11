/**
 * Data-driven navigation configuration.
 *
 * Defines menu items for each context (personal, business, platform)
 * with permission gates. The `useFilteredNav` hook filters items
 * based on the user's membership permissions.
 */

import {
  ArrowLeftRight,
  BarChart3,
  Bell,
  Building2,
  Compass,
  FileText,
  Globe,
  Heart,
  Home,
  Image,
  Key,
  LayoutDashboard,
  Newspaper,
  ScrollText,
  Settings,
  Shield,
  User,
  Users,
  Users2,
} from "lucide-react";

import type { NavContext, NavContextConfig } from "@/types/navigation";

// =============================================================================
// NAV CONFIG
// =============================================================================

export const NAV_CONFIG: NavContextConfig = {
  personal: [
    {
      label: "Main",
      items: [
        { key: "home", label: "Home", icon: Home, href: "/home", activeMatch: "exact" },
        { key: "explore", label: "Explore", icon: Compass, href: "/explore", activeMatch: "prefix" },
        { key: "network", label: "Network", icon: Users2, href: "/network", activeMatch: "prefix" },
        {
          key: "notifications",
          label: "Notifications",
          icon: Bell,
          href: "/notifications",
          activeMatch: "prefix",
        },
        {
          key: "activity",
          label: "Activity",
          icon: ArrowLeftRight,
          href: "/activity",
          activeMatch: "prefix",
        },
      ],
    },
    {
      label: "Account",
      items: [
        { key: "profile", label: "Profile", icon: User, href: "/profile", activeMatch: "prefix" },
        { key: "settings", label: "Settings", icon: Settings, href: "/settings", activeMatch: "exact" },
        { key: "sessions", label: "Security", icon: Shield, href: "/sessions", activeMatch: "exact" },
      ],
    },
  ],

  business: [
    {
      label: "Overview",
      items: [
        {
          key: "biz-dashboard",
          label: "Dashboard",
          icon: LayoutDashboard,
          href: "/bconsole/{slug}/dashboard",
          activeMatch: "exact",
        },
        {
          key: "biz-profile",
          label: "Profile",
          icon: User,
          href: "/bconsole/{slug}/profile",
          activeMatch: "exact",
        },
      ],
    },
    {
      label: "Team",
      items: [
        {
          key: "biz-members",
          label: "Members",
          icon: Users,
          href: "/bconsole/{slug}/members",
          permission: "can_view_members",
          minMembers: 2,
          activeMatch: "prefix",
        },
      ],
    },
    {
      label: "Network",
      items: [
        {
          key: "biz-followers",
          label: "Followers",
          icon: Heart,
          href: "/bconsole/{slug}/network/followers",
          permission: "can_manage_followers",
          activeMatch: "prefix",
        },
        {
          key: "biz-connections",
          label: "Connections",
          icon: Users2,
          href: "/bconsole/{slug}/network/connections",
          permission: "can_manage_connections",
          activeMatch: "prefix",
        },
      ],
    },
    {
      label: "Content",
      items: [
        {
          key: "biz-forms",
          label: "Forms",
          icon: FileText,
          href: "/bconsole/{slug}/forms",
          permission: "can_create_form",
          activeMatch: "prefix",
        },
        {
          key: "biz-content",
          label: "Content",
          icon: Newspaper,
          href: "/bconsole/{slug}/content",
          permission: "can_view_cms_content",
          activeMatch: "prefix",
        },
        {
          key: "biz-media",
          label: "Media",
          icon: Image,
          href: "/bconsole/{slug}/media",
          permission: "can_upload_cms_media",
          activeMatch: "prefix",
        },
      ],
    },
    {
      label: "Operations",
      items: [
        {
          key: "biz-transactions",
          label: "Transactions",
          icon: ScrollText,
          href: "/bconsole/{slug}/transactions",
          permission: "can_view_transactions",
          activeMatch: "prefix",
        },
        {
          key: "biz-audit",
          label: "Audit Log",
          icon: BarChart3,
          href: "/bconsole/{slug}/audit",
          permission: "can_view_audit_logs",
          activeMatch: "prefix",
        },
        {
          key: "biz-settings",
          label: "Settings",
          icon: Settings,
          href: "/bconsole/{slug}/settings",
          permission: "can_view_settings",
          activeMatch: "exact",
        },
      ],
    },
  ],

  platform: [
    {
      label: "Overview",
      items: [
        {
          key: "plat-dashboard",
          label: "Dashboard",
          icon: LayoutDashboard,
          href: "/pconsole/dashboard",
          activeMatch: "exact",
        },
        {
          key: "plat-profile",
          label: "Profile",
          icon: User,
          href: "/pconsole/profile",
          activeMatch: "exact",
        },
      ],
    },
    {
      label: "Management",
      items: [
        {
          key: "plat-businesses",
          label: "Businesses",
          icon: Building2,
          href: "/pconsole/businesses",
          permission: "can_view_businesses",
          activeMatch: "prefix",
        },
        {
          key: "plat-members",
          label: "Members",
          icon: Users,
          href: "/pconsole/members",
          permission: "can_view_members",
          minMembers: 2,
          activeMatch: "prefix",
        },
      ],
    },
    {
      label: "CMS",
      items: [
        {
          key: "plat-sites",
          label: "Sites",
          icon: Globe,
          href: "/pconsole/cms/sites",
          permission: "can_create_cms_site",
          activeMatch: "prefix",
        },
        {
          key: "plat-templates",
          label: "Templates",
          icon: FileText,
          href: "/pconsole/cms/templates",
          permission: "can_create_cms_template",
          activeMatch: "prefix",
        },
        {
          key: "plat-api-keys",
          label: "API Keys",
          icon: Key,
          href: "/pconsole/cms/api-keys",
          permission: "can_create_cms_api_key",
          activeMatch: "prefix",
        },
        {
          key: "plat-media",
          label: "Media",
          icon: Image,
          href: "/pconsole/media",
          permission: "can_upload_cms_media",
          activeMatch: "prefix",
        },
      ],
    },
    {
      label: "Operations",
      items: [
        {
          key: "plat-transactions",
          label: "Transactions",
          icon: ScrollText,
          href: "/pconsole/transactions",
          permission: "can_view_transactions",
          activeMatch: "prefix",
        },
        {
          key: "plat-audit",
          label: "Audit Log",
          icon: BarChart3,
          href: "/pconsole/audit",
          permission: "can_view_audit_logs",
          activeMatch: "prefix",
        },
        {
          key: "plat-settings",
          label: "Settings",
          icon: Settings,
          href: "/pconsole/settings",
          permission: "can_view_settings",
          activeMatch: "exact",
        },
      ],
    },
  ],
};

// =============================================================================
// HELPERS
// =============================================================================

/**
 * Resolve {slug} placeholder in href for business context.
 */
export function resolveHref(href: string, context: NavContext): string {
  if (context.type === "business") {
    return href.replace("{slug}", context.slug);
  }
  return href;
}

/**
 * Check if a pathname matches a nav item's href.
 */
export function isNavActive(pathname: string, href: string, match: "exact" | "prefix"): boolean {
  return match === "exact" ? pathname === href : pathname.startsWith(href);
}
