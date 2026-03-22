import { describe, it, expect, vi, beforeEach } from "vitest";

import {
  fetchTransactionsApi,
  fetchTransactionDetailApi,
  createInvitationApi,
  createRequestApi,
  acceptTransactionApi,
  denyTransactionApi,
  cancelTransactionApi,
  dismissTransactionApi,
  requestInfoApi,
  resubmitTransactionApi,
  approveTransactionApi,
  fetchTransactionFormResponseApi,
  updateTransactionFormResponseApi,
  fetchTransactionTypesApi,
  fetchFormMappingsApi,
  createFormMappingApi,
  deleteFormMappingApi,
} from "./transactions-api";

import type { PaginatedResponse } from "@/types";
import type {
  TransactionListItem,
  TransactionDetailWithPerms,
  TransactionTypeInfo,
  TransactionFormMapping,
} from "@/types/transactions";

vi.mock("@/lib/api-client", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}));

import { apiClient } from "@/lib/api-client";

const mockListItem: TransactionListItem = {
  id: "txn-1",
  transaction_type: "business_membership_invitation",
  initiator_type: "user",
  initiator_id: "550e8400-e29b-41d4-a716-446655440001",
  target_type: "account",
  target_id: "550e8400-e29b-41d4-a716-446655440002",
  mode: "invitation",
  status: "pending",
  category: "membership",
  initiator_name: "Alice",
  target_name: "Bob",
  context_type: "business",
  context_id: "biz-1",
  expires_at: null,
  created_at: "2026-01-01T00:00:00Z",
};

const mockDetail: TransactionDetailWithPerms = {
  id: "txn-1",
  transaction_type: "business_membership_invitation",
  mode: "invitation",
  initiator_type: "user",
  initiator_id: "user-1",
  initiator_context: {},
  initiator_name: "Alice",
  initiator_avatar_url: null,
  target_type: "user",
  target_id: "user-2",
  target_name: "Bob",
  target_avatar_url: null,
  context_type: "business",
  context_id: "biz-1",
  status: "pending",
  payload: {},
  form_response_id: null,
  info_requested_at: null,
  info_requested_message: null,
  info_requested_fields: null,
  expires_at: null,
  resolved_at: null,
  resolution_reason: "",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
  logs: [],
  form_response: null,
  form_mapping: null,
  _permissions: {
    can_accept: true,
    can_approve: false,
    can_deny: true,
    can_cancel: false,
    can_dismiss: false,
    can_request_info: false,
    can_resubmit: false,
    can_view_form: false,
  },
};

const mockPaginated: PaginatedResponse<TransactionListItem> = {
  count: 1,
  next: null,
  previous: null,
  results: [mockListItem],
};

beforeEach(() => {
  vi.clearAllMocks();
});

describe("fetchTransactionsApi", () => {
  it("calls GET /transactions/ with params", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: mockPaginated });

    const result = await fetchTransactionsApi({ mode: "invitation", status: "pending" });

    expect(apiClient.get).toHaveBeenCalledWith("/transactions/", {
      params: { mode: "invitation", status: "pending" },
    });
    expect(result.results).toHaveLength(1);
  });
});

describe("fetchTransactionDetailApi", () => {
  it("calls GET /transactions/<id>/ with _permissions", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: mockDetail });

    const result = await fetchTransactionDetailApi("txn-1");

    expect(apiClient.get).toHaveBeenCalledWith("/transactions/txn-1/");
    expect(result._permissions.can_accept).toBe(true);
  });
});

describe("createInvitationApi", () => {
  it("calls POST /transactions/invitation/", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: mockDetail });

    const input = {
      transaction_type: "business_membership_invitation",
      target_user_id: "user-2",
      context_type: "business",
      context_id: "biz-1",
    };
    await createInvitationApi(input);

    expect(apiClient.post).toHaveBeenCalledWith(
      "/transactions/invitation/",
      input,
    );
  });
});

describe("createRequestApi", () => {
  it("calls POST /transactions/request/", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: mockDetail });

    const input = {
      transaction_type: "business_membership_request",
      target_account_id: "biz-1",
      target_account_type: "business",
    };
    await createRequestApi(input);

    expect(apiClient.post).toHaveBeenCalledWith(
      "/transactions/request/",
      input,
    );
  });
});

describe("acceptTransactionApi", () => {
  it("calls POST /transactions/<id>/accept/ with role_id", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: mockDetail });

    await acceptTransactionApi("txn-1", { role_id: "role-1" });

    expect(apiClient.post).toHaveBeenCalledWith(
      "/transactions/txn-1/accept/",
      { role_id: "role-1" },
    );
  });

  it("sends empty object when no data", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: mockDetail });

    await acceptTransactionApi("txn-1");

    expect(apiClient.post).toHaveBeenCalledWith(
      "/transactions/txn-1/accept/",
      {},
    );
  });
});

describe("denyTransactionApi", () => {
  it("calls POST /transactions/<id>/deny/ with reason", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: mockDetail });

    await denyTransactionApi("txn-1", { reason: "Not qualified" });

    expect(apiClient.post).toHaveBeenCalledWith(
      "/transactions/txn-1/deny/",
      { reason: "Not qualified" },
    );
  });
});

describe("cancelTransactionApi", () => {
  it("calls POST /transactions/<id>/cancel/", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: mockDetail });

    await cancelTransactionApi("txn-1");

    expect(apiClient.post).toHaveBeenCalledWith(
      "/transactions/txn-1/cancel/",
      {},
    );
  });
});

describe("dismissTransactionApi", () => {
  it("calls POST /transactions/<id>/dismiss/", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: mockDetail });

    await dismissTransactionApi("txn-1");

    expect(apiClient.post).toHaveBeenCalledWith(
      "/transactions/txn-1/dismiss/",
      {},
    );
  });
});

describe("requestInfoApi", () => {
  it("calls POST /transactions/<id>/request-info/", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: mockDetail });

    await requestInfoApi("txn-1", {
      message: "Please provide more details",
      requested_fields: ["resume"],
    });

    expect(apiClient.post).toHaveBeenCalledWith(
      "/transactions/txn-1/request-info/",
      { message: "Please provide more details", requested_fields: ["resume"] },
    );
  });
});

describe("resubmitTransactionApi", () => {
  it("calls POST /transactions/<id>/resubmit/", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: mockDetail });

    await resubmitTransactionApi("txn-1");

    expect(apiClient.post).toHaveBeenCalledWith(
      "/transactions/txn-1/resubmit/",
      {},
    );
  });
});

describe("approveTransactionApi", () => {
  it("calls POST /transactions/<id>/approve/", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: mockDetail });

    await approveTransactionApi("txn-1");

    expect(apiClient.post).toHaveBeenCalledWith(
      "/transactions/txn-1/approve/",
      {},
    );
  });
});

describe("fetchTransactionFormResponseApi", () => {
  it("calls GET /transactions/<id>/form-response/", async () => {
    const mockFormResponse = { id: "fr-1", data: {} };
    vi.mocked(apiClient.get).mockResolvedValue({ data: mockFormResponse });

    const result = await fetchTransactionFormResponseApi("txn-1");

    expect(apiClient.get).toHaveBeenCalledWith(
      "/transactions/txn-1/form-response/",
    );
    expect(result.id).toBe("fr-1");
  });
});

describe("updateTransactionFormResponseApi", () => {
  it("calls PATCH /transactions/<id>/form-response/", async () => {
    const mockFormResponse = { id: "fr-1", data: { name: "Alice" } };
    vi.mocked(apiClient.patch).mockResolvedValue({ data: mockFormResponse });

    await updateTransactionFormResponseApi("txn-1", {
      data: { name: "Alice" },
    });

    expect(apiClient.patch).toHaveBeenCalledWith(
      "/transactions/txn-1/form-response/",
      { data: { name: "Alice" } },
    );
  });
});

describe("fetchTransactionTypesApi", () => {
  it("calls GET /transactions/types/ with context_type filter", async () => {
    const types: TransactionTypeInfo[] = [
      {
        id: "business_membership_invitation",
        name: "Business Membership Invitation",
        mode: "invitation",
        category: "membership",
        context_type: "business",
        requires_form: false,
        has_optional_form: true,
        user_configurable: true,
        expiration_days: 7,
      },
    ];
    vi.mocked(apiClient.get).mockResolvedValue({ data: types });

    const result = await fetchTransactionTypesApi("business");

    expect(apiClient.get).toHaveBeenCalledWith("/transactions/types/", {
      params: { context_type: "business" },
    });
    expect(result).toHaveLength(1);
  });

  it("calls without params when no context_type", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: [] });

    await fetchTransactionTypesApi();

    expect(apiClient.get).toHaveBeenCalledWith("/transactions/types/", {
      params: undefined,
    });
  });
});

describe("fetchFormMappingsApi", () => {
  it("calls GET /transactions/form-mappings/", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: [] });

    await fetchFormMappingsApi({ account_type: "business", account_id: "biz-1" });

    expect(apiClient.get).toHaveBeenCalledWith("/transactions/form-mappings/", {
      params: { account_type: "business", account_id: "biz-1" },
    });
  });
});

describe("createFormMappingApi", () => {
  it("calls POST /transactions/form-mappings/", async () => {
    const mockMapping: TransactionFormMapping = {
      id: "map-1",
      account_type: "business",
      account_id: "biz-1",
      transaction_type: "business_membership_invitation",
      form_template_id: "tpl-1",
      form_template_name: "App Form",
      is_required: true,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    };
    vi.mocked(apiClient.post).mockResolvedValue({ data: mockMapping });

    await createFormMappingApi({
      account_type: "business",
      account_id: "550e8400-e29b-41d4-a716-446655440002",
      transaction_type: "business_membership_invitation",
      form_template_id: "tpl-1",
      is_required: true,
    });

    expect(apiClient.post).toHaveBeenCalledWith(
      "/transactions/form-mappings/",
      {
        account_type: "business",
        account_id: "550e8400-e29b-41d4-a716-446655440002",
        transaction_type: "business_membership_invitation",
        form_template_id: "tpl-1",
        is_required: true,
      },
    );
  });
});

describe("deleteFormMappingApi", () => {
  it("calls DELETE /transactions/form-mappings/<id>/", async () => {
    vi.mocked(apiClient.delete).mockResolvedValue({ data: undefined });

    await deleteFormMappingApi("map-1");

    expect(apiClient.delete).toHaveBeenCalledWith(
      "/transactions/form-mappings/map-1/",
    );
  });
});
