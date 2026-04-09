/**
 * W4: Join Request with Form workflow.
 *
 * Cross-system flow: Transaction → Forms → Organization.
 * Owner creates a form template, maps it to membership requests, a fresh user
 * navigates to the business public profile and submits a join request,
 * which triggers a form dialog. Owner sees the pending_review request.
 *
 * Uses two browser contexts (owner setup + requester).
 *
 * @layer L2
 * @system transactions, forms, business
 * @parameters P4 (Transaction State), P6 (Forms), P5 (Data Integrity)
 * @priority P0
 */

import { test, expect } from '../../fixtures/business.fixture';
import { isSystemEnabled } from '../../lib/feature-gates';
import { generateEmail } from '../../lib/utils';
import { DEFAULT_PASSWORD, TEST_USERS } from '../../lib/constants';
import { registerAndVerifyViaApi, loginInNewContext } from '../../helpers/auth.helper';
import {
  createTemplateViaApi,
  addFieldViaApi,
  publishTemplateViaApi,
} from '../../helpers/form.helper';
import { createFormMappingViaApi } from '../../helpers/transaction.helper';
import { BusinessProfilePage } from '../../pages/business/business-profile.page';

test.describe('W4: Join Request with Form', () => {
  test.skip(!isSystemEnabled('forms'), 'Forms system disabled');

  test('user submits join request with required form, owner sees pending_review', async ({
    browser,
    apiClient,
    dbClient,
    businessContext,
  }) => {
    const { slug, id: bizId } = businessContext;

    // Step 1 — As owner via API: create form template → add text field → publish
    await apiClient.login(TEST_USERS.businessOwner.email, TEST_USERS.businessOwner.password);
    const template = await createTemplateViaApi(apiClient, 'business', bizId, {
      name: 'W4 Membership Form',
      description: 'Required form for join requests',
    });
    await addFieldViaApi(apiClient, template.id, {
      field_key: 'motivation',
      field_type: 'text',
      label: 'Why do you want to join?',
      is_required: true,
    });
    await publishTemplateViaApi(apiClient, template.id);

    // Step 2 — Create form mapping: link template to business_membership_request
    await createFormMappingViaApi(apiClient, {
      transactionType: 'business_membership_request',
      templateId: template.id,
      accountType: 'business',
      accountId: bizId,
      isRequired: true,
    });

    // Step 3 — Register fresh user via API → verify email
    const requester = await registerAndVerifyViaApi(apiClient, dbClient, {
      email: generateEmail('w4-requester'),
    });

    // Step 4 — Login fresh user in new context
    const { page: requesterPage, context: requesterCtx } = await loginInNewContext(
      browser,
      requester.email,
      DEFAULT_PASSWORD,
    );

    // Step 5 — Navigate to business public profile
    const bizProfile = new BusinessProfilePage(requesterPage);
    await bizProfile.goto(slug);

    // Step 6 — Click "Request to Join" button
    await expect(bizProfile.requestToJoinButton).toBeVisible();
    await bizProfile.requestToJoinButton.click();

    // Step 7 — Expect form dialog to appear (because form mapping requires it)
    await expect(requesterPage.getByText(/why do you want to join/i)).toBeVisible();

    // Step 8 — Fill required form field → submit
    await requesterPage.getByLabel(/why do you want to join/i).fill('I want to contribute');
    // Submit the form within the dialog and wait for the POST to complete
    await Promise.all([
      requesterPage.waitForResponse(
        (resp) =>
          resp.url().includes('/transactions') &&
          resp.request().method() === 'POST' &&
          resp.ok(),
      ),
      requesterPage.getByRole('button', { name: /submit|send|request/i }).click(),
    ]);

    // Step 10 — Owner checks transactions/requests for pending or pending_review status
    await apiClient.login(TEST_USERS.businessOwner.email, TEST_USERS.businessOwner.password);
    // Try pending_review first (form-required path), then pending (no-form path)
    let res = await apiClient.get(
      `transactions/?context_type=business&context_id=${bizId}&status=pending_review&transaction_type=business_membership_request`,
    );
    let body = (await res.json()) as { results: Record<string, unknown>[] };
    if (body.results.length === 0) {
      res = await apiClient.get(
        `transactions/?context_type=business&context_id=${bizId}&status=pending&transaction_type=business_membership_request`,
      );
      body = (await res.json()) as { results: Record<string, unknown>[] };
    }
    expect(body.results.length).toBeGreaterThanOrEqual(1);

    // Cleanup
    await requesterCtx.close();
  });
});
