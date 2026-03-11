import { describe, it, expect, vi, beforeEach } from "vitest";

import {
  fetchTemplatesApi,
  createTemplateApi,
  fetchTemplateDetailApi,
  updateTemplateApi,
  deleteTemplateApi,
  publishTemplateApi,
  archiveTemplateApi,
  forkTemplateApi,
  fetchLibraryApi,
  addFieldApi,
  updateFieldApi,
  deleteFieldApi,
  reorderFieldsApi,
  fetchResponsesApi,
  createResponseApi,
  fetchResponseDetailApi,
  updateResponseApi,
  submitResponseApi,
  processResponseApi,
  voidResponseApi,
  fetchMyResponsesApi,
} from "./forms-api";

import type { PaginatedResponse } from "@/types";
import type {
  FormTemplateList,
  FormTemplateDetailWithPerms,
  FormField,
  FormResponseList,
  FormResponseDetail,
} from "@/types/forms";

vi.mock("@/lib/api-client", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}));

import { apiClient } from "@/lib/api-client";

// ---------------------------------------------------------------------------
// Mock data
// ---------------------------------------------------------------------------

const mockField: FormField = {
  id: "field-1",
  field_key: "full_name",
  field_type: "text",
  label: "Full Name",
  description: "",
  placeholder: "Enter your name",
  order: 0,
  step_tag: "",
  section_tag: "",
  options: [],
  validation_rules: {},
  ui_config: {},
  default_value: null,
  is_required: true,
  is_indexed: false,
  is_hidden: false,
  is_readonly: false,
};

const mockTemplateList: FormTemplateList = {
  id: "tpl-1",
  name: "Application Form",
  slug: "application-form",
  description: "Standard application form",
  owner_type: "business",
  scope: "business",
  status: "active",
  version: 1,
  is_current: true,
  is_template_public: false,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

const mockTemplateDetail: FormTemplateDetailWithPerms = {
  id: "tpl-1",
  name: "Application Form",
  slug: "application-form",
  description: "Standard application form",
  owner_type: "business",
  owner_id: "acc-1",
  scope: "business",
  status: "active",
  version: 1,
  is_current: true,
  parent_version: null,
  is_template_public: false,
  forked_from: null,
  forked_from_name: null,
  settings: {},
  fields: [mockField],
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
  _permissions: {
    can_edit: true,
    can_delete: true,
    can_publish: true,
    can_archive: false,
  },
};

const mockPaginatedTemplates: PaginatedResponse<FormTemplateList> = {
  count: 1,
  next: null,
  previous: null,
  results: [mockTemplateList],
};

const mockResponseList: FormResponseList = {
  id: "resp-1",
  form_template: "tpl-1",
  form_name: "Application Form",
  form_version: 1,
  submitted_by: "user-1",
  submitter_email: "alice@example.com",
  submitter_username: "alice",
  submitter_display_name: "Alice Smith",
  data: { full_name: "Alice Smith" },
  status: "submitted",
  submitted_at: "2026-01-02T00:00:00Z",
  processed_at: null,
  created_at: "2026-01-01T00:00:00Z",
};

const mockResponseDetail: FormResponseDetail = {
  id: "resp-1",
  form_template: "tpl-1",
  form_name: "Application Form",
  form_version: 1,
  submitted_by: "user-1",
  submitter_email: "alice@example.com",
  submitter_username: "alice",
  submitter_display_name: "Alice Smith",
  submitter_context: {},
  data: { full_name: "Alice" },
  status: "submitted",
  submitted_at: "2026-01-02T00:00:00Z",
  processed_at: null,
  processed_by: null,
  processor_email: null,
  processor_notes: "",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

const mockPaginatedResponses: PaginatedResponse<FormResponseList> = {
  count: 1,
  next: null,
  previous: null,
  results: [mockResponseList],
};

beforeEach(() => {
  vi.clearAllMocks();
});

// ---------------------------------------------------------------------------
// Template APIs
// ---------------------------------------------------------------------------

describe("fetchTemplatesApi", () => {
  it("calls GET /forms/<accountType>/<accountId>/templates/", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: mockPaginatedTemplates,
    });

    const result = await fetchTemplatesApi("business", "acc-1", {
      status: "active",
    });

    expect(apiClient.get).toHaveBeenCalledWith(
      "/forms/business/acc-1/templates/",
      { params: { status: "active" } },
    );
    expect(result.results).toHaveLength(1);
  });
});

describe("createTemplateApi", () => {
  it("calls POST /forms/<accountType>/<accountId>/templates/", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: mockTemplateDetail });

    const input = {
      name: "New Form",
      owner_type: "business" as const,
      scope: "business" as const,
    };
    const result = await createTemplateApi("business", "acc-1", input);

    expect(apiClient.post).toHaveBeenCalledWith(
      "/forms/business/acc-1/templates/",
      input,
    );
    expect(result.id).toBe("tpl-1");
  });
});

describe("fetchTemplateDetailApi", () => {
  it("calls GET /forms/templates/<formId>/ with _permissions", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: mockTemplateDetail });

    const result = await fetchTemplateDetailApi("tpl-1");

    expect(apiClient.get).toHaveBeenCalledWith("/forms/templates/tpl-1/");
    expect(result._permissions.can_edit).toBe(true);
  });
});

describe("updateTemplateApi", () => {
  it("calls PATCH /forms/templates/<formId>/", async () => {
    vi.mocked(apiClient.patch).mockResolvedValue({ data: mockTemplateDetail });

    await updateTemplateApi("tpl-1", { name: "Updated Form" });

    expect(apiClient.patch).toHaveBeenCalledWith("/forms/templates/tpl-1/", {
      name: "Updated Form",
    });
  });
});

describe("deleteTemplateApi", () => {
  it("calls DELETE /forms/templates/<formId>/", async () => {
    vi.mocked(apiClient.delete).mockResolvedValue({ data: undefined });

    await deleteTemplateApi("tpl-1");

    expect(apiClient.delete).toHaveBeenCalledWith("/forms/templates/tpl-1/");
  });
});

describe("publishTemplateApi", () => {
  it("calls POST /forms/templates/<formId>/publish/", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: mockTemplateDetail });

    await publishTemplateApi("tpl-1");

    expect(apiClient.post).toHaveBeenCalledWith(
      "/forms/templates/tpl-1/publish/",
      {},
    );
  });
});

describe("archiveTemplateApi", () => {
  it("calls POST /forms/templates/<formId>/archive/", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: mockTemplateDetail });

    await archiveTemplateApi("tpl-1");

    expect(apiClient.post).toHaveBeenCalledWith(
      "/forms/templates/tpl-1/archive/",
      {},
    );
  });
});

describe("forkTemplateApi", () => {
  it("calls POST /forms/templates/<formId>/fork/", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: mockTemplateDetail });

    const input = {
      new_owner_type: "business" as const,
      new_owner_id: "acc-2",
    };
    await forkTemplateApi("tpl-1", input);

    expect(apiClient.post).toHaveBeenCalledWith(
      "/forms/templates/tpl-1/fork/",
      input,
    );
  });
});

describe("fetchLibraryApi", () => {
  it("calls GET /forms/templates/library/", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: mockPaginatedTemplates,
    });

    const result = await fetchLibraryApi({ scope: "business" });

    expect(apiClient.get).toHaveBeenCalledWith("/forms/templates/library/", {
      params: { scope: "business" },
    });
    expect(result.count).toBe(1);
  });
});

// ---------------------------------------------------------------------------
// Field APIs
// ---------------------------------------------------------------------------

describe("addFieldApi", () => {
  it("calls POST /forms/templates/<formId>/fields/", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: mockField });

    const input = {
      field_key: "email",
      field_type: "email" as const,
      label: "Email Address",
      order: 1,
    };
    const result = await addFieldApi("tpl-1", input);

    expect(apiClient.post).toHaveBeenCalledWith(
      "/forms/templates/tpl-1/fields/",
      input,
    );
    expect(result.id).toBe("field-1");
  });
});

describe("updateFieldApi", () => {
  it("calls PATCH /forms/templates/<templateId>/fields/<fieldId>/", async () => {
    vi.mocked(apiClient.patch).mockResolvedValue({ data: mockField });

    await updateFieldApi("tpl-1", "field-1", { label: "New Label" });

    expect(apiClient.patch).toHaveBeenCalledWith(
      "/forms/templates/tpl-1/fields/field-1/",
      { label: "New Label" },
    );
  });
});

describe("deleteFieldApi", () => {
  it("calls DELETE /forms/templates/<templateId>/fields/<fieldId>/", async () => {
    vi.mocked(apiClient.delete).mockResolvedValue({ data: undefined });

    await deleteFieldApi("tpl-1", "field-1");

    expect(apiClient.delete).toHaveBeenCalledWith(
      "/forms/templates/tpl-1/fields/field-1/",
    );
  });
});

describe("reorderFieldsApi", () => {
  it("calls POST /forms/templates/<templateId>/fields/reorder/", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: [mockField] });

    const fields = [
      { field_id: "field-1", order: 0 },
      { field_id: "field-2", order: 1 },
    ];
    const result = await reorderFieldsApi("tpl-1", fields);

    expect(apiClient.post).toHaveBeenCalledWith(
      "/forms/templates/tpl-1/fields/reorder/",
      { fields },
    );
    expect(result).toHaveLength(1);
  });
});

// ---------------------------------------------------------------------------
// Response APIs
// ---------------------------------------------------------------------------

describe("fetchResponsesApi", () => {
  it("calls GET /forms/templates/<formId>/responses/ with params", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: mockPaginatedResponses,
    });

    const result = await fetchResponsesApi("tpl-1", { status: "submitted" });

    expect(apiClient.get).toHaveBeenCalledWith(
      "/forms/templates/tpl-1/responses/",
      { params: { status: "submitted" } },
    );
    expect(result.results).toHaveLength(1);
  });
});

describe("createResponseApi", () => {
  it("calls POST /forms/templates/<formId>/responses/", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: mockResponseDetail });

    const result = await createResponseApi("tpl-1", {
      data: { full_name: "Alice" },
    });

    expect(apiClient.post).toHaveBeenCalledWith(
      "/forms/templates/tpl-1/responses/",
      { data: { full_name: "Alice" } },
    );
    expect(result.id).toBe("resp-1");
  });
});

describe("fetchResponseDetailApi", () => {
  it("calls GET /forms/responses/<responseId>/", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: mockResponseDetail });

    const result = await fetchResponseDetailApi("resp-1");

    expect(apiClient.get).toHaveBeenCalledWith("/forms/responses/resp-1/");
    expect(result.data).toEqual({ full_name: "Alice" });
  });
});

describe("updateResponseApi", () => {
  it("calls PATCH /forms/responses/<responseId>/", async () => {
    vi.mocked(apiClient.patch).mockResolvedValue({ data: mockResponseDetail });

    await updateResponseApi("resp-1", { data: { full_name: "Bob" } });

    expect(apiClient.patch).toHaveBeenCalledWith("/forms/responses/resp-1/", {
      data: { full_name: "Bob" },
    });
  });
});

describe("submitResponseApi", () => {
  it("calls POST /forms/responses/<responseId>/submit/", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: mockResponseDetail });

    await submitResponseApi("resp-1");

    expect(apiClient.post).toHaveBeenCalledWith(
      "/forms/responses/resp-1/submit/",
      {},
    );
  });
});

describe("processResponseApi", () => {
  it("calls POST /forms/responses/<responseId>/process/ with notes", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: mockResponseDetail });

    await processResponseApi("resp-1", { notes: "Approved" });

    expect(apiClient.post).toHaveBeenCalledWith(
      "/forms/responses/resp-1/process/",
      { notes: "Approved" },
    );
  });

  it("sends empty object when no data", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: mockResponseDetail });

    await processResponseApi("resp-1");

    expect(apiClient.post).toHaveBeenCalledWith(
      "/forms/responses/resp-1/process/",
      {},
    );
  });
});

describe("voidResponseApi", () => {
  it("calls POST /forms/responses/<responseId>/void/ with reason", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: mockResponseDetail });

    await voidResponseApi("resp-1", { reason: "Duplicate" });

    expect(apiClient.post).toHaveBeenCalledWith(
      "/forms/responses/resp-1/void/",
      { reason: "Duplicate" },
    );
  });
});

describe("fetchMyResponsesApi", () => {
  it("calls GET /forms/me/responses/ with params", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: mockPaginatedResponses,
    });

    const result = await fetchMyResponsesApi({ form_id: "tpl-1" });

    expect(apiClient.get).toHaveBeenCalledWith("/forms/me/responses/", {
      params: { form_id: "tpl-1" },
    });
    expect(result.results).toHaveLength(1);
  });
});
