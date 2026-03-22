import { renderHook, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

import { createWrapper } from "@/test/utils";
import {
  useCreateInvitation,
  useAcceptTransaction,
  useDenyTransaction,
  useCancelTransaction,
  useApproveTransaction,
  useCreateFormMapping,
  useDeleteFormMapping,
} from "./use-transaction-mutations";

vi.mock("@/features/transactions/api/transactions-api", () => ({
  createInvitationApi: vi.fn().mockResolvedValue({ id: "txn-new" }),
  acceptTransactionApi: vi.fn().mockResolvedValue({ id: "txn-1" }),
  denyTransactionApi: vi.fn().mockResolvedValue({ id: "txn-1" }),
  cancelTransactionApi: vi.fn().mockResolvedValue({ id: "txn-1" }),
  approveTransactionApi: vi.fn().mockResolvedValue({ id: "txn-1" }),
  createFormMappingApi: vi.fn().mockResolvedValue({ id: "map-new" }),
  deleteFormMappingApi: vi.fn().mockResolvedValue(undefined),
}));

import {
  createInvitationApi,
  acceptTransactionApi,
  denyTransactionApi,
  cancelTransactionApi,
  approveTransactionApi,
  createFormMappingApi,
  deleteFormMappingApi,
} from "@/features/transactions/api/transactions-api";

beforeEach(() => {
  vi.clearAllMocks();
});

describe("useCreateInvitation", () => {
  it("calls createInvitationApi with correct args", async () => {
    const { result } = renderHook(() => useCreateInvitation(), {
      wrapper: createWrapper(),
    });

    const input = {
      transaction_type: "business_membership_invitation",
      target_user_id: "user-2",
      context_type: "business",
      context_id: "biz-1",
    };
    result.current.mutate(input);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(createInvitationApi).toHaveBeenCalledWith(input);
  });
});

describe("useAcceptTransaction", () => {
  it("calls acceptTransactionApi with role_id", async () => {
    const { result } = renderHook(() => useAcceptTransaction(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({
      transactionId: "txn-1",
      data: { role_id: "role-1" },
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(acceptTransactionApi).toHaveBeenCalledWith("txn-1", {
      role_id: "role-1",
    });
  });
});

describe("useDenyTransaction", () => {
  it("calls denyTransactionApi with reason", async () => {
    const { result } = renderHook(() => useDenyTransaction(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({
      transactionId: "txn-1",
      data: { reason: "Not qualified" },
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(denyTransactionApi).toHaveBeenCalledWith("txn-1", {
      reason: "Not qualified",
    });
  });
});

describe("useApproveTransaction", () => {
  it("calls approveTransactionApi", async () => {
    const { result } = renderHook(() => useApproveTransaction(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({ transactionId: "txn-1" });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(approveTransactionApi).toHaveBeenCalledWith("txn-1");
  });
});

describe("useCancelTransaction", () => {
  it("calls cancelTransactionApi", async () => {
    const { result } = renderHook(() => useCancelTransaction(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({ transactionId: "txn-1" });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(cancelTransactionApi).toHaveBeenCalledWith("txn-1");
  });
});

describe("useCreateFormMapping", () => {
  it("calls createFormMappingApi", async () => {
    const { result } = renderHook(
      () => useCreateFormMapping("business", "biz-1"),
      { wrapper: createWrapper() },
    );

    result.current.mutate({
      account_type: "business",
      account_id: "550e8400-e29b-41d4-a716-446655440002",
      transaction_type: "business_membership_invitation",
      form_template_id: "tpl-1",
      is_required: true,
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(createFormMappingApi).toHaveBeenCalledWith({
      account_type: "business",
      account_id: "550e8400-e29b-41d4-a716-446655440002",
      transaction_type: "business_membership_invitation",
      form_template_id: "tpl-1",
      is_required: true,
    });
  });
});

describe("useDeleteFormMapping", () => {
  it("calls deleteFormMappingApi with mappingId", async () => {
    const { result } = renderHook(
      () => useDeleteFormMapping("business", "biz-1"),
      { wrapper: createWrapper() },
    );

    result.current.mutate("map-1");

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(deleteFormMappingApi).toHaveBeenCalledWith("map-1");
  });
});
