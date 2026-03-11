import { renderHook, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

import { createWrapper } from "@/test/utils";
import {
  useCreateTemplate,
  useUpdateTemplate,
  useDeleteTemplate,
  usePublishTemplate,
  useArchiveTemplate,
  useForkTemplate,
  useAddField,
  useUpdateField,
  useDeleteField,
  useReorderFields,
  useCreateResponse,
  useSubmitResponse,
  useProcessResponse,
  useVoidResponse,
} from "./use-form-mutations";

vi.mock("@/features/forms/api/forms-api", () => ({
  createTemplateApi: vi.fn().mockResolvedValue({ id: "tpl-new" }),
  updateTemplateApi: vi.fn().mockResolvedValue({ id: "tpl-1" }),
  deleteTemplateApi: vi.fn().mockResolvedValue(undefined),
  publishTemplateApi: vi.fn().mockResolvedValue({ id: "tpl-1" }),
  archiveTemplateApi: vi.fn().mockResolvedValue({ id: "tpl-1" }),
  forkTemplateApi: vi.fn().mockResolvedValue({ id: "tpl-forked" }),
  addFieldApi: vi.fn().mockResolvedValue({ id: "field-new" }),
  updateFieldApi: vi.fn().mockResolvedValue({ id: "field-1" }),
  deleteFieldApi: vi.fn().mockResolvedValue(undefined),
  reorderFieldsApi: vi.fn().mockResolvedValue([]),
  createResponseApi: vi.fn().mockResolvedValue({ id: "resp-new" }),
  updateResponseApi: vi.fn().mockResolvedValue({ id: "resp-1" }),
  submitResponseApi: vi.fn().mockResolvedValue({ id: "resp-1" }),
  processResponseApi: vi.fn().mockResolvedValue({ id: "resp-1" }),
  voidResponseApi: vi.fn().mockResolvedValue({ id: "resp-1" }),
}));

import {
  createTemplateApi,
  deleteTemplateApi,
  publishTemplateApi,
  forkTemplateApi,
  addFieldApi,
  deleteFieldApi,
  reorderFieldsApi,
  createResponseApi,
  submitResponseApi,
  processResponseApi,
  voidResponseApi,
} from "@/features/forms/api/forms-api";

beforeEach(() => {
  vi.clearAllMocks();
});

// ---------------------------------------------------------------------------
// Template mutations
// ---------------------------------------------------------------------------

describe("useCreateTemplate", () => {
  it("calls createTemplateApi with correct args", async () => {
    const { result } = renderHook(
      () => useCreateTemplate("business", "acc-1"),
      { wrapper: createWrapper() },
    );

    result.current.mutate({
      name: "New Form",
      owner_type: "business",
      scope: "business",
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(createTemplateApi).toHaveBeenCalledWith("business", "acc-1", {
      name: "New Form",
      owner_type: "business",
      scope: "business",
    });
  });
});

describe("useDeleteTemplate", () => {
  it("calls deleteTemplateApi with formId", async () => {
    const { result } = renderHook(
      () => useDeleteTemplate("business", "acc-1"),
      { wrapper: createWrapper() },
    );

    result.current.mutate("tpl-1");

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(deleteTemplateApi).toHaveBeenCalledWith("tpl-1");
  });
});

describe("usePublishTemplate", () => {
  it("calls publishTemplateApi", async () => {
    const { result } = renderHook(
      () => usePublishTemplate("business", "acc-1", "tpl-1"),
      { wrapper: createWrapper() },
    );

    result.current.mutate();

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(publishTemplateApi).toHaveBeenCalledWith("tpl-1");
  });
});

describe("useForkTemplate", () => {
  it("calls forkTemplateApi with formId and data", async () => {
    const { result } = renderHook(() => useForkTemplate(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({
      formId: "tpl-1",
      data: { new_owner_type: "business", new_owner_id: "acc-2" },
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(forkTemplateApi).toHaveBeenCalledWith("tpl-1", {
      new_owner_type: "business",
      new_owner_id: "acc-2",
    });
  });
});

// ---------------------------------------------------------------------------
// Field mutations
// ---------------------------------------------------------------------------

describe("useAddField", () => {
  it("calls addFieldApi with correct args", async () => {
    const { result } = renderHook(() => useAddField("tpl-1"), {
      wrapper: createWrapper(),
    });

    result.current.mutate({
      field_key: "name",
      field_type: "text",
      label: "Name",
      order: 0,
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(addFieldApi).toHaveBeenCalledWith("tpl-1", {
      field_key: "name",
      field_type: "text",
      label: "Name",
      order: 0,
    });
  });
});

describe("useDeleteField", () => {
  it("calls deleteFieldApi with fieldId", async () => {
    const { result } = renderHook(() => useDeleteField("tpl-1"), {
      wrapper: createWrapper(),
    });

    result.current.mutate("field-1");

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(deleteFieldApi).toHaveBeenCalledWith("tpl-1", "field-1");
  });
});

describe("useReorderFields", () => {
  it("calls reorderFieldsApi with field order array", async () => {
    const { result } = renderHook(() => useReorderFields("tpl-1"), {
      wrapper: createWrapper(),
    });

    const fields = [
      { field_id: "field-1", order: 0 },
      { field_id: "field-2", order: 1 },
    ];
    result.current.mutate(fields);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(reorderFieldsApi).toHaveBeenCalledWith("tpl-1", fields);
  });
});

// ---------------------------------------------------------------------------
// Response mutations
// ---------------------------------------------------------------------------

describe("useCreateResponse", () => {
  it("calls createResponseApi with form data", async () => {
    const { result } = renderHook(() => useCreateResponse("tpl-1"), {
      wrapper: createWrapper(),
    });

    result.current.mutate({ data: { name: "Alice" } });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(createResponseApi).toHaveBeenCalledWith("tpl-1", {
      data: { name: "Alice" },
    });
  });
});

describe("useSubmitResponse", () => {
  it("calls submitResponseApi with responseId", async () => {
    const { result } = renderHook(() => useSubmitResponse("tpl-1"), {
      wrapper: createWrapper(),
    });

    result.current.mutate("resp-1");

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(submitResponseApi).toHaveBeenCalledWith("resp-1");
  });
});

describe("useProcessResponse", () => {
  it("calls processResponseApi with notes", async () => {
    const { result } = renderHook(() => useProcessResponse("tpl-1"), {
      wrapper: createWrapper(),
    });

    result.current.mutate({
      responseId: "resp-1",
      data: { notes: "Approved" },
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(processResponseApi).toHaveBeenCalledWith("resp-1", {
      notes: "Approved",
    });
  });
});

describe("useVoidResponse", () => {
  it("calls voidResponseApi with reason", async () => {
    const { result } = renderHook(() => useVoidResponse("tpl-1"), {
      wrapper: createWrapper(),
    });

    result.current.mutate({
      responseId: "resp-1",
      data: { reason: "Duplicate" },
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(voidResponseApi).toHaveBeenCalledWith("resp-1", {
      reason: "Duplicate",
    });
  });
});
