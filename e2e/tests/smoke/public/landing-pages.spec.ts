/**
 * Public landing pages smoke tests.
 *
 * @layer L1
 * @system public
 * @parameters P1, P3
 * @priority P0
 */

import { test, expect } from '@playwright/test';
import { LandingPage, AboutPage, ContactPage } from '../../../pages/public/landing.page';
import { checkLandmarks } from '../../../lib/a11y-checks';

test.describe('Landing Pages', () => {
  test('landing page renders with heading and navigation', async ({ page }) => {
    const landingPage = new LandingPage(page);
    await landingPage.goto();

    await expect(landingPage.heading).toBeVisible();
    await expect(landingPage.brandLink).toBeVisible();
  });

  test('public navigation links are visible', async ({ page }) => {
    const landingPage = new LandingPage(page);
    await landingPage.goto();

    await expect(landingPage.exploreLink).toBeVisible();
    await expect(landingPage.aboutLink).toBeVisible();
    await expect(landingPage.contactLink).toBeVisible();
    await expect(landingPage.signInButton).toBeVisible();
    await expect(landingPage.registerButton).toBeVisible();
  });

  test('about page renders', async ({ page }) => {
    const aboutPage = new AboutPage(page);
    await aboutPage.goto();

    await expect(aboutPage.heading).toBeVisible();
    await expect(aboutPage.heading).toContainText(/about/i);
  });

  test('contact page renders', async ({ page }) => {
    const contactPage = new ContactPage(page);
    await contactPage.goto();

    await expect(contactPage.heading).toBeVisible();
    await expect(contactPage.heading).toContainText(/contact/i);
  });

  test('sign in link navigates to login', async ({ page }) => {
    const landingPage = new LandingPage(page);
    await landingPage.goto();

    await landingPage.signInButton.click();
    await expect(page).toHaveURL(/\/login/);
  });

  test('register link navigates to register', async ({ page }) => {
    const landingPage = new LandingPage(page);
    await landingPage.goto();

    await landingPage.registerButton.click();
    await expect(page).toHaveURL(/\/register/);
  });

  test('explore link navigates to explore page', async ({ page }) => {
    const landingPage = new LandingPage(page);
    await landingPage.goto();

    await landingPage.exploreLink.click();
    await expect(page).toHaveURL(/\/explore/);
  });

  // --- Visual Regression ---
  test('landing page visual regression', async ({ page }) => {
    const landingPage = new LandingPage(page);
    await landingPage.goto();
    await expect(page).toHaveScreenshot('landing-page.png');
  });

  test('about page visual regression', async ({ page }) => {
    const aboutPage = new AboutPage(page);
    await aboutPage.goto();
    await expect(page).toHaveScreenshot('about-page.png');
  });

  test('contact page visual regression', async ({ page }) => {
    const contactPage = new ContactPage(page);
    await contactPage.goto();
    await expect(page).toHaveScreenshot('contact-page.png');
  });

  // --- Accessibility ---
  test('landing page has correct ARIA landmarks', async ({ page }) => {
    const landingPage = new LandingPage(page);
    await landingPage.goto();
    await checkLandmarks(page, { expectBanner: true });
  });
});
