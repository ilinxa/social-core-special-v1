import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { Home, Settings } from "lucide-react";

import type { NavContext, NavItem as NavItemType } from "@/types/navigation";

import { NavItem } from "./NavItem";

// =============================================================================
// MOCKS
// =============================================================================

vi.mock("next/link", () => ({
  default: ({ children, href, ...props }: { children: React.ReactNode; href: string; [key: string]: unknown }) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

// =============================================================================
// FIXTURES
// =============================================================================

const personalContext: NavContext = { type: "personal" };

const businessContext: NavContext = {
  type: "business",
  slug: "acme",
  accountId: "acc-1",
  accountName: "Acme Corp",
};

const homeItem: NavItemType = {
  key: "home",
  label: "Home",
  icon: Home,
  href: "/home",
  activeMatch: "exact",
};

const bizSettingsItem: NavItemType = {
  key: "biz-settings",
  label: "Settings",
  icon: Settings,
  href: "/bconsole/{slug}/settings",
  activeMatch: "exact",
};

// =============================================================================
// TESTS
// =============================================================================

describe("NavItem", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders a link with the correct href and label", () => {
    render(<NavItem item={homeItem} context={personalContext} active={false} />);

    const link = screen.getByRole("link", { name: /home/i });
    expect(link).toBeInTheDocument();
    expect(link).toHaveAttribute("href", "/home");
  });

  it("sets aria-current='page' when active is true", () => {
    render(<NavItem item={homeItem} context={personalContext} active={true} />);

    const link = screen.getByRole("link", { name: /home/i });
    expect(link).toHaveAttribute("aria-current", "page");
  });

  it("does not set aria-current when active is false", () => {
    render(<NavItem item={homeItem} context={personalContext} active={false} />);

    const link = screen.getByRole("link", { name: /home/i });
    expect(link).not.toHaveAttribute("aria-current");
  });

  it("resolves {slug} placeholder for business context", () => {
    render(
      <NavItem item={bizSettingsItem} context={businessContext} active={false} />,
    );

    const link = screen.getByRole("link", { name: /settings/i });
    expect(link).toHaveAttribute("href", "/bconsole/acme/settings");
  });

  it("leaves {slug} unresolved for personal context (passthrough)", () => {
    render(
      <NavItem item={bizSettingsItem} context={personalContext} active={false} />,
    );

    const link = screen.getByRole("link", { name: /settings/i });
    expect(link).toHaveAttribute("href", "/bconsole/{slug}/settings");
  });
});
