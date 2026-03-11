import { renderHook, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

import { createWrapper } from "@/test/utils";
import {
  useChangeMemberRole,
  useSuspendMember,
  useRemoveMember,
  useBanMember,
  useReactivateMember,
  useLeaveMember,
} from "./use-member-mutations";

vi.mock("@/features/members/api/members-api", () => ({
  changeMemberRoleApi: vi.fn().mockResolvedValue(undefined),
  suspendMemberApi: vi.fn().mockResolvedValue(undefined),
  removeMemberApi: vi.fn().mockResolvedValue(undefined),
  banMemberApi: vi.fn().mockResolvedValue(undefined),
  reactivateMemberApi: vi.fn().mockResolvedValue(undefined),
  leaveMemberApi: vi.fn().mockResolvedValue(undefined),
}));

import {
  changeMemberRoleApi,
  suspendMemberApi,
  removeMemberApi,
  banMemberApi,
  reactivateMemberApi,
  leaveMemberApi,
} from "@/features/members/api/members-api";

beforeEach(() => {
  vi.clearAllMocks();
});

describe("useChangeMemberRole", () => {
  it("calls changeMemberRoleApi with correct args", async () => {
    const { result } = renderHook(
      () => useChangeMemberRole("business", "test-biz"),
      { wrapper: createWrapper() },
    );

    result.current.mutate({
      membershipId: "mem-1",
      data: { role_id: "role-2" },
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(changeMemberRoleApi).toHaveBeenCalledWith(
      "business",
      "test-biz",
      "mem-1",
      { role_id: "role-2" },
    );
  });
});

describe("useSuspendMember", () => {
  it("calls suspendMemberApi with reason", async () => {
    const { result } = renderHook(
      () => useSuspendMember("business", "test-biz"),
      { wrapper: createWrapper() },
    );

    result.current.mutate({
      membershipId: "mem-1",
      data: { reason: "Policy violation" },
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(suspendMemberApi).toHaveBeenCalledWith(
      "business",
      "test-biz",
      "mem-1",
      { reason: "Policy violation" },
    );
  });
});

describe("useRemoveMember", () => {
  it("calls removeMemberApi", async () => {
    const { result } = renderHook(
      () => useRemoveMember("business", "test-biz"),
      { wrapper: createWrapper() },
    );

    result.current.mutate({ membershipId: "mem-1" });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(removeMemberApi).toHaveBeenCalledWith(
      "business",
      "test-biz",
      "mem-1",
      undefined,
    );
  });
});

describe("useBanMember", () => {
  it("calls banMemberApi with reason", async () => {
    const { result } = renderHook(
      () => useBanMember("business", "test-biz"),
      { wrapper: createWrapper() },
    );

    result.current.mutate({
      membershipId: "mem-1",
      data: { reason: "Spam" },
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(banMemberApi).toHaveBeenCalledWith(
      "business",
      "test-biz",
      "mem-1",
      { reason: "Spam" },
    );
  });
});

describe("useReactivateMember", () => {
  it("calls reactivateMemberApi", async () => {
    const { result } = renderHook(
      () => useReactivateMember("business", "test-biz"),
      { wrapper: createWrapper() },
    );

    result.current.mutate({ membershipId: "mem-1" });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(reactivateMemberApi).toHaveBeenCalledWith(
      "business",
      "test-biz",
      "mem-1",
    );
  });
});

describe("useLeaveMember", () => {
  it("calls leaveMemberApi", async () => {
    const { result } = renderHook(
      () => useLeaveMember("business", "test-biz"),
      { wrapper: createWrapper() },
    );

    result.current.mutate();

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(leaveMemberApi).toHaveBeenCalledWith("business", "test-biz");
  });
});
