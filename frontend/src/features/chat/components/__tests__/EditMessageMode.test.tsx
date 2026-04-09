import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, within, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "@/test/utils";
import { EditMessageMode } from "../EditMessageMode";

const mockMutateAsync = vi.fn().mockResolvedValue({});

vi.mock("@/features/chat/hooks/use-chat-mutations", () => ({
  useEditMessage: () => ({
    mutateAsync: mockMutateAsync,
    isPending: false,
  }),
}));

function getActionButtons() {
  const container = screen.getByTestId("edit-message-mode");
  const allButtons = within(container).getAllByRole("button");
  return {
    cancelButton: allButtons[allButtons.length - 2],
    saveButton: allButtons[allButtons.length - 1],
  };
}

describe("EditMessageMode", () => {
  const mockOnCancel = vi.fn();
  const mockOnComplete = vi.fn();

  const defaultProps = {
    conversationId: "conv-1",
    messageId: "msg-1",
    initialContent: "Hello world",
    onCancel: mockOnCancel,
    onComplete: mockOnComplete,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders editing banner text", () => {
    renderWithProviders(<EditMessageMode {...defaultProps} />);

    expect(screen.getByText("Editing message")).toBeInTheDocument();
  });

  it("shows initial content in textarea", () => {
    renderWithProviders(<EditMessageMode {...defaultProps} />);

    const textarea = screen.getByRole("textbox");
    expect(textarea).toHaveValue("Hello world");
  });

  it("cancel button calls onCancel", async () => {
    const user = userEvent.setup();
    renderWithProviders(<EditMessageMode {...defaultProps} />);

    const { cancelButton } = getActionButtons();
    await user.click(cancelButton);

    expect(mockOnCancel).toHaveBeenCalledOnce();
  });

  it("Escape key calls onCancel", async () => {
    const user = userEvent.setup();
    renderWithProviders(<EditMessageMode {...defaultProps} />);

    const textarea = screen.getByRole("textbox");
    await user.click(textarea);
    await user.keyboard("{Escape}");

    expect(mockOnCancel).toHaveBeenCalledOnce();
  });

  it("save button is disabled when content is unchanged", () => {
    renderWithProviders(<EditMessageMode {...defaultProps} />);

    const { saveButton } = getActionButtons();
    expect(saveButton).toBeDisabled();
  });

  it("save button is disabled when content is empty", async () => {
    const user = userEvent.setup();
    renderWithProviders(<EditMessageMode {...defaultProps} />);

    const textarea = screen.getByRole("textbox");
    await user.clear(textarea);

    const { saveButton } = getActionButtons();
    expect(saveButton).toBeDisabled();
  });

  it("save calls mutateAsync with correct params", async () => {
    const user = userEvent.setup();
    renderWithProviders(<EditMessageMode {...defaultProps} />);

    const textarea = screen.getByRole("textbox");
    await user.clear(textarea);
    await user.type(textarea, "Updated message");

    const { saveButton } = getActionButtons();
    await user.click(saveButton);

    await waitFor(() => {
      expect(mockMutateAsync).toHaveBeenCalledWith({
        messageId: "msg-1",
        data: { content: "Updated message" },
      });
    });
  });

  it("calls onComplete after successful save", async () => {
    const user = userEvent.setup();
    renderWithProviders(<EditMessageMode {...defaultProps} />);

    const textarea = screen.getByRole("textbox");
    await user.clear(textarea);
    await user.type(textarea, "Updated message");

    const { saveButton } = getActionButtons();
    await user.click(saveButton);

    await waitFor(() => {
      expect(mockOnComplete).toHaveBeenCalledOnce();
    });
  });
});
