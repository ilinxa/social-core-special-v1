import { describe, it, expect } from "vitest";

import {
  conversationDetailQueryOptions,
  participantsQueryOptions,
  unreadCountsQueryOptions,
} from "./use-chat-queries";

// =============================================================================
// conversationDetailQueryOptions
// =============================================================================

describe("conversationDetailQueryOptions", () => {
  it("returns correct query key", () => {
    const opts = conversationDetailQueryOptions("conv-1");

    expect(opts.queryKey).toEqual(["chat", "conversation", "conv-1"]);
  });

  it("uses 5-minute staleTime", () => {
    const opts = conversationDetailQueryOptions("conv-1");

    expect(opts.staleTime).toBe(5 * 60 * 1000);
  });

  it("enables query when conversationId is provided", () => {
    const opts = conversationDetailQueryOptions("conv-1");

    expect(opts.enabled).toBe(true);
  });

  it("disables query when conversationId is empty", () => {
    const opts = conversationDetailQueryOptions("");

    expect(opts.enabled).toBe(false);
  });
});

// =============================================================================
// participantsQueryOptions
// =============================================================================

describe("participantsQueryOptions", () => {
  it("returns correct query key", () => {
    const opts = participantsQueryOptions("conv-1");

    expect(opts.queryKey).toEqual(["chat", "participants", "conv-1"]);
  });

  it("uses 60-second staleTime", () => {
    const opts = participantsQueryOptions("conv-1");

    expect(opts.staleTime).toBe(60 * 1000);
  });

  it("enables query when conversationId is provided", () => {
    const opts = participantsQueryOptions("conv-1");

    expect(opts.enabled).toBe(true);
  });

  it("disables query when conversationId is empty", () => {
    const opts = participantsQueryOptions("");

    expect(opts.enabled).toBe(false);
  });
});

// =============================================================================
// unreadCountsQueryOptions
// =============================================================================

describe("unreadCountsQueryOptions", () => {
  it("returns correct query key", () => {
    const opts = unreadCountsQueryOptions();

    expect(opts.queryKey).toEqual(["chat", "unread"]);
  });

  it("uses 30-second staleTime", () => {
    const opts = unreadCountsQueryOptions();

    expect(opts.staleTime).toBe(30 * 1000);
  });

  it("uses 30-second refetchInterval", () => {
    const opts = unreadCountsQueryOptions();

    expect(opts.refetchInterval).toBe(30_000);
  });
});
