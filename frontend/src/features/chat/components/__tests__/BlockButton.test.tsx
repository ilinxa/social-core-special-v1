import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { BlockButton } from "../BlockButton";

const mockBlockMutate = vi.fn();
vi.mock("@/features/chat/hooks/use-chat-mutations", () => ({
  useBlockParticipant: () => ({ mutate: mockBlockMutate, isPending: false }),
}));

describe("BlockButton", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders block button", () => {
    render(
      <BlockButton
        blockedType="user"
        blockedId="user-123"
        blockedName="John Doe"
      />
    );

    expect(screen.getByTestId("block-button")).toBeInTheDocument();
    expect(screen.getByText("Block")).toBeInTheDocument();
  });

  it("clicking block button opens confirmation dialog", async () => {
    const user = userEvent.setup();
    render(
      <BlockButton
        blockedType="user"
        blockedId="user-123"
        blockedName="John Doe"
      />
    );

    await user.click(screen.getByTestId("block-button"));

    expect(screen.getByText("Block John Doe?")).toBeInTheDocument();
  });

  it("shows warning description text", async () => {
    const user = userEvent.setup();
    render(
      <BlockButton
        blockedType="user"
        blockedId="user-123"
        blockedName="John Doe"
      />
    );

    await user.click(screen.getByTestId("block-button"));

    expect(
      screen.getByText(/will no longer receive messages from John Doe/i)
    ).toBeInTheDocument();
  });

  it("confirming calls block.mutate with correct params", async () => {
    const user = userEvent.setup();
    render(
      <BlockButton
        blockedType="user"
        blockedId="user-123"
        blockedName="John Doe"
      />
    );

    await user.click(screen.getByTestId("block-button"));
    const confirmButton = screen.getByRole("button", { name: "Block" });
    await user.click(confirmButton);

    expect(mockBlockMutate).toHaveBeenCalledWith({
      blocked_type: "user",
      blocked_id: "user-123",
    });
  });

  it("cancel closes dialog", async () => {
    const user = userEvent.setup();
    render(
      <BlockButton
        blockedType="user"
        blockedId="user-123"
        blockedName="John Doe"
      />
    );

    await user.click(screen.getByTestId("block-button"));
    expect(screen.getByText("Block John Doe?")).toBeInTheDocument();

    const cancelButton = screen.getByRole("button", { name: "Cancel" });
    await user.click(cancelButton);

    expect(screen.queryByText("Block John Doe?")).not.toBeInTheDocument();
  });
});
