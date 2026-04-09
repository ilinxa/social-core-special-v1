/**
 * Form helper — common form operations for tests.
 *
 * Provides API-based template and response setup.
 *
 * Django URL structure (under /api/v1/forms/):
 *   - {account_type}/{account_id}/templates/       → list/create
 *   - templates/{form_id}/                         → detail
 *   - templates/{form_id}/publish/                 → publish
 *   - templates/{form_id}/archive/                 → archive
 *   - templates/{form_id}/fields/                  → add field
 *   - templates/{form_id}/responses/               → list/create responses
 *   - templates/library/                           → public library
 */

import type { ApiClient } from '../lib/api-client';

/** Create a form template via API (scoped to account). */
export async function createTemplateViaApi(
  api: ApiClient,
  accountType: string,
  accountId: string,
  data: {
    name: string;
    slug?: string;
    description?: string;
  },
): Promise<{ id: string; name: string; status: string; version: number }> {
  const res = await api.post(
    `forms/${accountType}/${accountId}/templates/`,
    {
      ...data,
      owner_type: accountType,
      owner_id: accountId,
      scope: accountType,
    },
  );
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`createTemplateViaApi failed (${res.status}): ${body}`);
  }
  return (await res.json()) as {
    id: string;
    name: string;
    status: string;
    version: number;
  };
}

/** Add a field to a form template via API. */
export async function addFieldViaApi(
  api: ApiClient,
  templateId: string,
  data: {
    field_key: string;
    field_type: string;
    label: string;
    is_required?: boolean;
    description?: string;
    order?: number;
  },
): Promise<{ id: string; field_key: string }> {
  const res = await api.post(`forms/templates/${templateId}/fields/`, {
    ...data,
    template_id: templateId,
    order: data.order ?? 0,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`addFieldViaApi failed (${res.status}): ${body}`);
  }
  return (await res.json()) as { id: string; field_key: string };
}

/** Publish a form template via API. */
export async function publishTemplateViaApi(
  api: ApiClient,
  templateId: string,
): Promise<void> {
  const res = await api.post(`forms/templates/${templateId}/publish/`);
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`publishTemplateViaApi failed (${res.status}): ${body}`);
  }
}

/** Archive a form template via API. */
export async function archiveTemplateViaApi(
  api: ApiClient,
  templateId: string,
): Promise<void> {
  await api.post(`forms/templates/${templateId}/archive/`);
}

/** Get a form template via API. */
export async function getTemplateViaApi(
  api: ApiClient,
  templateId: string,
): Promise<Record<string, unknown>> {
  const res = await api.get(`forms/templates/${templateId}/`);
  return (await res.json()) as Record<string, unknown>;
}

/** List form templates via API (scoped to account). */
export async function listTemplatesViaApi(
  api: ApiClient,
  accountType: string,
  accountId: string,
): Promise<{ results: Record<string, unknown>[] }> {
  const res = await api.get(
    `forms/${accountType}/${accountId}/templates/`,
  );
  return (await res.json()) as { results: Record<string, unknown>[] };
}

/** Submit a form response via API. */
export async function submitResponseViaApi(
  api: ApiClient,
  templateId: string,
  fieldValues: Record<string, unknown>,
): Promise<{ id: string; status: string }> {
  const res = await api.post(`forms/templates/${templateId}/responses/`, {
    data: fieldValues,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`submitResponseViaApi failed (${res.status}): ${body}`);
  }
  return (await res.json()) as { id: string; status: string };
}
