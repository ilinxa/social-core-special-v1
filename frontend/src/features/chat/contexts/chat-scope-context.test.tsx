import { renderHook } from "@testing-library/react";
import { describe, it, expect } from "vitest";

import {
  ChatScopeProvider,
  useChatScope,
  type ChatScopeValue,
} from "./chat-scope-context";

function createWrapper(value: ChatScopeValue) {
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <ChatScopeProvider value={value}>{children}</ChatScopeProvider>
    );
  };
}

describe("ChatScopeProvider + useChatScope", () => {
  it("provides global scope value", () => {
    const scopeValue: ChatScopeValue = {
      scopeType: "global",
      scopeId: null,
    };

    const { result } = renderHook(() => useChatScope(), {
      wrapper: createWrapper(scopeValue),
    });

    expect(result.current.scopeType).toBe("global");
    expect(result.current.scopeId).toBeNull();
  });

  it("provides business scope with scopeId and slug", () => {
    const scopeValue: ChatScopeValue = {
      scopeType: "business",
      scopeId: "biz-123",
      slug: "my-business",
    };

    const { result } = renderHook(() => useChatScope(), {
      wrapper: createWrapper(scopeValue),
    });

    expect(result.current.scopeType).toBe("business");
    expect(result.current.scopeId).toBe("biz-123");
    expect(result.current.slug).toBe("my-business");
  });

  it("provides platform scope value", () => {
    const scopeValue: ChatScopeValue = {
      scopeType: "platform",
      scopeId: "plat-456",
    };

    const { result } = renderHook(() => useChatScope(), {
      wrapper: createWrapper(scopeValue),
    });

    expect(result.current.scopeType).toBe("platform");
    expect(result.current.scopeId).toBe("plat-456");
  });

  it("provides entity participant info", () => {
    const scopeValue: ChatScopeValue = {
      scopeType: "global",
      scopeId: null,
      participantType: "business",
      participantId: "biz-123",
    };

    const { result } = renderHook(() => useChatScope(), {
      wrapper: createWrapper(scopeValue),
    });

    expect(result.current.participantType).toBe("business");
    expect(result.current.participantId).toBe("biz-123");
  });

  it("throws when used outside provider", () => {
    expect(() => {
      renderHook(() => useChatScope());
    }).toThrow("useChatScope must be used within a ChatScopeProvider");
  });
});
