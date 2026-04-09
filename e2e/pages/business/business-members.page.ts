/**
 * Business Members Page Object Models.
 *
 * Members route: /bconsole/[slug]/members
 * Member detail route: /bconsole/[slug]/members/[id]
 * Role detail route: /bconsole/[slug]/members/roles/[id]
 */

import type { Page, Locator } from '@playwright/test';
import { BasePage } from '../base.page';

export class BusinessMembersPage extends BasePage {
  readonly heading: Locator;

  // --- Search ---
  readonly searchInput: Locator;

  // --- Tabs (status filter) ---
  readonly allTab: Locator;
  readonly activeTab: Locator;

  // --- Role list ---
  readonly rolesHeading: Locator;
  readonly createRoleButton: Locator;

  // --- Empty state ---
  readonly emptyMessage: Locator;

  // --- Quota ---
  readonly quotaBar: Locator;

  constructor(page: Page) {
    super(page);
    this.heading = page.getByRole('heading', { level: 1, name: /members/i });

    // Search
    this.searchInput = page.getByPlaceholder(/search members/i);

    // Status tabs
    this.allTab = page.getByRole('tab', { name: /all/i }).or(
      page.getByRole('button', { name: /^all$/i }),
    );
    this.activeTab = page.getByRole('tab', { name: /active/i }).or(
      page.getByRole('button', { name: /^active$/i }),
    );

    // Roles
    this.rolesHeading = page.getByRole('heading', { name: /roles/i });
    this.createRoleButton = page.getByRole('button', { name: /create role/i });

    // Empty
    this.emptyMessage = page.getByText(/no members found/i);

    // Quota — look for the progressbar first; the "1 / 10" text is near the top
    this.quotaBar = page.getByRole('progressbar').first();
  }

  async goto(slug: string): Promise<void> {
    await this.page.goto(`/bconsole/${slug}/members`);
  }

  /** Get a member card by display name or username. */
  getMemberCard(name: string | RegExp): Locator {
    return this.page.getByRole('button', { name });
  }

  /** Get a role card by name. */
  getRoleCard(name: string | RegExp): Locator {
    return this.page.getByText(name);
  }
}

export class MemberDetailPage extends BasePage {
  // --- Navigation ---
  readonly backButton: Locator;

  // --- Member info ---
  readonly memberName: Locator;
  readonly memberEmail: Locator;
  readonly memberUsername: Locator;
  readonly roleBadge: Locator;
  readonly statusBadge: Locator;
  readonly ownerBadge: Locator;

  // --- Actions ---
  readonly changeRoleButton: Locator;
  readonly suspendButton: Locator;
  readonly removeButton: Locator;
  readonly banButton: Locator;
  readonly reactivateButton: Locator;

  constructor(page: Page) {
    super(page);

    // Nav
    this.backButton = page.getByRole('button', { name: /back to members/i });

    // Info — Badge renders role.name as outline variant, StatusBadge renders status text
    this.memberName = page.getByRole('heading', { level: 3 }).first();
    this.memberEmail = page.getByText(/@[\w.-]+\.[\w]+/);
    this.memberUsername = page.getByText(/^@/);
    this.roleBadge = page.getByRole('heading', { name: /member info/i });
    this.statusBadge = page.getByText(/active|suspended|banned|removed|pending/i).first();
    this.ownerBadge = page.getByText('Owner');

    // Actions
    this.changeRoleButton = page.getByRole('button', { name: /change role/i });
    this.suspendButton = page.getByRole('button', { name: /^suspend$/i });
    this.removeButton = page.getByRole('button', { name: /^remove$/i });
    this.banButton = page.getByRole('button', { name: /^ban$/i });
    this.reactivateButton = page.getByRole('button', { name: /reactivate/i });
  }

  async goto(slug: string, memberId: string): Promise<void> {
    await this.page.goto(`/bconsole/${slug}/members/${memberId}`);
  }
}

export class RoleDetailPage extends BasePage {
  // --- Navigation ---
  readonly backButton: Locator;

  // --- Role info ---
  readonly roleDetailsHeading: Locator;
  readonly roleName: Locator;
  readonly systemBadge: Locator;
  readonly levelBadge: Locator;

  // --- Actions ---
  readonly editButton: Locator;
  readonly deleteButton: Locator;
  readonly saveButton: Locator;
  readonly cancelButton: Locator;

  // --- Edit fields ---
  readonly nameInput: Locator;
  readonly descriptionInput: Locator;

  // --- Permissions ---
  readonly permissionsHeading: Locator;

  constructor(page: Page) {
    super(page);

    // Nav
    this.backButton = page.getByRole('button', { name: /back to members/i });

    // Info — role name renders as <p class="font-medium">, not a heading
    this.roleDetailsHeading = page.getByRole('heading', { name: /role details/i });
    this.roleName = page.getByText(/^[\w\s]+$/).first();
    this.systemBadge = page.getByText('System');
    this.levelBadge = page.getByText(/level \d+/i);

    // Actions
    this.editButton = page.getByRole('button', { name: /^edit$/i });
    this.deleteButton = page.getByRole('button', { name: /^delete$/i });
    this.saveButton = page.getByRole('button', { name: /^save$/i });
    this.cancelButton = page.getByRole('button', { name: /^cancel$/i });

    // Edit fields
    this.nameInput = page.getByLabel('Name');
    this.descriptionInput = page.getByLabel('Description');

    // Permissions
    this.permissionsHeading = page.getByRole('heading', { name: /permissions/i });
  }

  async goto(slug: string, roleId: string): Promise<void> {
    await this.page.goto(`/bconsole/${slug}/members/roles/${roleId}`);
  }
}
