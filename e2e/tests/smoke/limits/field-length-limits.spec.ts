/**
 * Field length validation smoke tests.
 *
 * Verifies that submitting form data exceeding max length limits
 * shows inline validation errors. Uses registration form (username
 * max 30 chars) and business profile edit (tagline max 500 chars).
 *
 * @layer L1
 * @system auth, business, limits
 * @parameters P1, P5, P10
 * @priority P2
 */

import { test, expect } from '../../../fixtures/business.fixture';
import { RegisterPage } from '../../../pages/auth/register.page';
import { BusinessProfileEditPage } from '../../../pages/business/business-console.page';

test.describe('Field Length Limits', () => {
  test('register form rejects username exceeding 30 characters', async ({ page }) => {
    const registerPage = new RegisterPage(page);
    await registerPage.goto();

    // Username max is 30 chars per Zod schema
    const longUsername = 'a'.repeat(31);
    await registerPage.register(
      `e2e-length-${Date.now()}@test.com`,
      longUsername,
      'TestPass123!',
    );

    // Zod custom message: "Username must be at most 30 characters"
    await expect(
      page.getByText(/username must be at most 30 characters/i),
    ).toBeVisible();
  });

  test('business profile rejects tagline exceeding 500 characters', async ({ businessOwnerPage, businessContext }) => {
    const page = businessOwnerPage;
    const profilePage = new BusinessProfileEditPage(page);
    await profilePage.goto(businessContext.slug);

    // Wait for form to fully load (heading appears during skeleton too)
    await expect(profilePage.taglineInput).toBeVisible({ timeout: 15000 });

    // Fill tagline with > 500 chars
    const longTagline = 'x'.repeat(501);
    await profilePage.taglineInput.fill(longTagline);
    await profilePage.saveButton.click();

    // Zod v4: "Too big: expected string to have <=500 characters"
    await expect(
      page.getByText(/<=500 character|at most 500 character/i),
    ).toBeVisible();
  });

  test('business profile rejects description exceeding 5000 characters', async ({ businessOwnerPage, businessContext }) => {
    const page = businessOwnerPage;
    const profilePage = new BusinessProfileEditPage(page);
    await profilePage.goto(businessContext.slug);

    // Wait for form to fully load (heading appears during skeleton too)
    await expect(profilePage.descriptionInput).toBeVisible({ timeout: 15000 });

    // Fill description with > 5000 chars
    const longDescription = 'y'.repeat(5001);
    await profilePage.descriptionInput.fill(longDescription);
    await profilePage.saveButton.click();

    // Zod v4: "Too big: expected string to have <=5000 characters"
    await expect(
      page.getByText(/<=5000 character|at most 5000 character/i),
    ).toBeVisible();
  });
});
