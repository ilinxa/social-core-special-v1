import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { ChatPage } from "../ChatPage";
import type { ChatScopeValue } from "../../contexts/chat-scope-context";

// Mock the child components
vi.mock("../ChatLayout", () => ({
  ChatLayout: ({ showEntityInbox }: { showEntityInbox?: boolean }) => (
    <div data-testid="chat-layout" data-entity-inbox={showEntityInbox}>
      ChatLayout
    </div>
  ),
}));

vi.mock("../ChatLayoutWrapper", () => ({
  ChatLayoutWrapper: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="chat-layout-wrapper">{children}</div>
  ),
}));

// Mock the ChatScopeProvider
vi.mock("../../contexts/chat-scope-context", () => ({
  ChatScopeProvider: ({
    children,
    value,
  }: {
    children: React.ReactNode;
    value: ChatScopeValue;
  }) => (
    <div data-testid="chat-scope-provider" data-scope={JSON.stringify(value)}>
      {children}
    </div>
  ),
}));

describe("ChatPage", () => {
  const mockScope: ChatScopeValue = {
    scopeType: "global",
    scopeId: null,
  };

  it("renders ChatLayout inside ChatLayoutWrapper", () => {
    render(<ChatPage scope={mockScope} />);

    expect(screen.getByTestId("chat-layout-wrapper")).toBeInTheDocument();
    expect(screen.getByTestId("chat-layout")).toBeInTheDocument();
  });

  it("passes showEntityInbox prop to ChatLayout when true", () => {
    render(<ChatPage scope={mockScope} showEntityInbox={true} />);

    const chatLayout = screen.getByTestId("chat-layout");
    expect(chatLayout).toHaveAttribute("data-entity-inbox", "true");
  });

  it("passes showEntityInbox prop to ChatLayout when false", () => {
    render(<ChatPage scope={mockScope} showEntityInbox={false} />);

    const chatLayout = screen.getByTestId("chat-layout");
    expect(chatLayout).toHaveAttribute("data-entity-inbox", "false");
  });

  it("does not pass showEntityInbox prop when undefined", () => {
    render(<ChatPage scope={mockScope} />);

    const chatLayout = screen.getByTestId("chat-layout");
    // showEntityInbox defaults to false when undefined
    expect(chatLayout).toHaveAttribute("data-entity-inbox", "false");
  });

  it("provides global scope context", () => {
    const globalScope: ChatScopeValue = {
      scopeType: "global",
      scopeId: null,
    };

    render(<ChatPage scope={globalScope} />);

    const provider = screen.getByTestId("chat-scope-provider");
    expect(provider).toHaveAttribute(
      "data-scope",
      JSON.stringify(globalScope)
    );
  });

  it("provides business scope context", () => {
    const businessScope: ChatScopeValue = {
      scopeType: "business",
      scopeId: "123e4567-e89b-12d3-a456-426614174000",
    };

    render(<ChatPage scope={businessScope} />);

    const provider = screen.getByTestId("chat-scope-provider");
    expect(provider).toHaveAttribute(
      "data-scope",
      JSON.stringify(businessScope)
    );
  });

  it("provides platform scope context", () => {
    const platformScope: ChatScopeValue = {
      scopeType: "platform",
      scopeId: "platform-id",
    };

    render(<ChatPage scope={platformScope} />);

    const provider = screen.getByTestId("chat-scope-provider");
    expect(provider).toHaveAttribute(
      "data-scope",
      JSON.stringify(platformScope)
    );
  });

  it("wraps components in correct order: Provider > Wrapper > Layout", () => {
    render(<ChatPage scope={mockScope} />);

    const provider = screen.getByTestId("chat-scope-provider");
    const wrapper = screen.getByTestId("chat-layout-wrapper");
    const layout = screen.getByTestId("chat-layout");

    // Verify nesting order
    expect(provider).toContainElement(wrapper);
    expect(wrapper).toContainElement(layout);
  });
});
