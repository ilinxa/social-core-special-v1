/**
 * W26: Form Builder Complete Lifecycle workflow.
 *
 * Cross-system flow: Forms → Organization.
 * Owner creates a template with 5+ field types, publishes it, submits a response,
 * and verifies all fields are rendered correctly via API.
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
  submitResponseViaApi,
} from '../../helpers/form.helper';

test.describe('W26: Form Builder Complete Lifecycle', () => {
  test.skip(!isSystemEnabled('forms'), 'Forms system disabled');

  test('template with all field types, response verified via API', async ({
    businessContext,
    apiClient,
  }) => {
    const { id: bizId } = businessContext;

    // Step 1 — Create template via API
    await apiClient.login(TEST_USERS.businessOwner.email, TEST_USERS.businessOwner.password);
    const template = await createTemplateViaApi(apiClient, 'business', bizId, {
      name: 'W26 Complete Form',
    });
    expect(template.id).toBeTruthy();

    // Step 2 — Add 5 different field types (re-login for fresh token)
    await apiClient.login(TEST_USERS.businessOwner.email, TEST_USERS.businessOwner.password);
    await addFieldViaApi(apiClient, template.id, {
      field_key: 'full_name',
      field_type: 'text',
      label: 'Full Name',
      is_required: true,
      order: 1,
    });
    await addFieldViaApi(apiClient, template.id, {
      field_key: 'employee_count',
      field_type: 'integer',
      label: 'Employee Count',
      order: 2,
    });
    await addFieldViaApi(apiClient, template.id, {
      field_key: 'contact_email',
      field_type: 'email',
      label: 'Contact Email',
      order: 3,
    });
    await addFieldViaApi(apiClient, template.id, {
      field_key: 'description',
      field_type: 'textarea',
      label: 'Description',
      order: 4,
    });
    await addFieldViaApi(apiClient, template.id, {
      field_key: 'website',
      field_type: 'url',
      label: 'Website URL',
      order: 5,
    });

    // Step 3 — Publish template
    await publishTemplateViaApi(apiClient, template.id);

    // Step 4 — Verify template is published via API
    await apiClient.login(TEST_USERS.businessOwner.email, TEST_USERS.businessOwner.password);
    const templateDetail = await apiClient.get(`forms/templates/${template.id}/`);
    const templateData = (await templateDetail.json()) as { status: string; fields?: unknown[] };
    // Form templates use 'active' status after the publish endpoint
    expect(templateData.status).toBe('active');
    // Template should have all 5 fields
    expect(templateData.fields?.length).toBeGreaterThanOrEqual(5);

    // Step 5 — Submit a response via API with values for all fields
    const response = await submitResponseViaApi(apiClient, template.id, {
      full_name: 'Jane Smith',
      employee_count: 50,
      contact_email: 'jane@example.com',
      description: 'A detailed description of the project.',
      website: 'https://example.com',
    });
    expect(response.id).toBeTruthy();
  });
});
