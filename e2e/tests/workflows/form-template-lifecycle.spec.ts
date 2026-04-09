/**
 * W19: Form Template Lifecycle workflow.
 *
 * Cross-system flow: Forms → Organization.
 * Owner creates a form template, adds fields, publishes it,
 * and verifies the complete lifecycle via API.
 *
 * @layer L2
 * @system forms, business
 * @parameters P5 (Data Integrity), P6 (Forms)
 * @priority P1
 */

import { test, expect } from '../../fixtures/business.fixture';
import { isSystemEnabled } from '../../lib/feature-gates';
import { TEST_USERS } from '../../lib/constants';
import {
  createTemplateViaApi,
  addFieldViaApi,
  publishTemplateViaApi,
  getTemplateViaApi,
  submitResponseViaApi,
} from '../../helpers/form.helper';

test.describe('W19: Form Template Lifecycle', () => {
  test.skip(!isSystemEnabled('forms'), 'Forms system disabled');

  test('owner creates template, adds fields, publishes, and submits response', async ({
    businessContext,
    apiClient,
  }) => {
    const { id: bizId } = businessContext;

    // Step 1 — Create template via API (business scope)
    await apiClient.login(TEST_USERS.businessOwner.email, TEST_USERS.businessOwner.password);
    const template = await createTemplateViaApi(apiClient, 'business', bizId, {
      name: 'W19 Lifecycle Form',
    });
    expect(template.id).toBeTruthy();

    // Step 2 — Add 3 fields (text, integer, text)
    // Re-login to ensure fresh token for all field additions
    await apiClient.login(TEST_USERS.businessOwner.email, TEST_USERS.businessOwner.password);
    await addFieldViaApi(apiClient, template.id, {
      field_key: 'name',
      field_type: 'text',
      label: 'Full Name',
      is_required: true,
      order: 1,
    });
    await addFieldViaApi(apiClient, template.id, {
      field_key: 'age',
      field_type: 'integer',
      label: 'Age',
      order: 2,
    });
    await addFieldViaApi(apiClient, template.id, {
      field_key: 'department',
      field_type: 'text',
      label: 'Department',
      order: 3,
    });

    // Step 3 — Publish template
    await publishTemplateViaApi(apiClient, template.id);

    // Step 4 — Verify template details via API
    const templateDetail = await getTemplateViaApi(apiClient, template.id);
    // Form templates use 'active' status after the publish endpoint
    expect(templateDetail.status).toBe('active');

    // Step 5 — Verify template has all 3 fields via API
    await apiClient.login(TEST_USERS.businessOwner.email, TEST_USERS.businessOwner.password);
    const fieldsRes = await apiClient.get(`forms/templates/${template.id}/`);
    const fieldsData = (await fieldsRes.json()) as { fields?: { field_key: string }[] };
    expect(fieldsData.fields?.length).toBeGreaterThanOrEqual(3);

    // Step 6 — Submit a response via API and verify
    const response = await submitResponseViaApi(apiClient, template.id, {
      name: 'John Doe',
      age: 30,
      department: 'Engineering',
    });
    expect(response.id).toBeTruthy();
  });
});
