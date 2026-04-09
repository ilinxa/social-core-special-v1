import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AttachmentPreview } from "../AttachmentPreview";
import type { PendingAttachment } from "../AttachmentPreview";

const createMockPendingAttachment = (
  id: string,
  overrides?: Partial<PendingAttachment>,
): PendingAttachment => ({
  id,
  file: new File(["test"], `test-${id}.jpg`, { type: "image/jpeg" }),
  previewUrl: `blob:http://localhost/preview-${id}`,
  uploading: false,
  ...overrides,
});

describe("AttachmentPreview", () => {
  const mockOnRemove = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("returns null for empty array", () => {
    const { container } = render(
      <AttachmentPreview attachments={[]} onRemove={mockOnRemove} />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders thumbnails for pending attachments", () => {
    const attachments = [
      createMockPendingAttachment("1"),
      createMockPendingAttachment("2"),
      createMockPendingAttachment("3"),
    ];
    render(
      <AttachmentPreview attachments={attachments} onRemove={mockOnRemove} />,
    );

    const container = screen.getByTestId("attachment-preview");
    expect(container).toBeInTheDocument();

    const images = screen.getAllByRole("img");
    expect(images).toHaveLength(3);
    expect(images[0]).toHaveAttribute("alt", "test-1.jpg");
    expect(images[1]).toHaveAttribute("alt", "test-2.jpg");
    expect(images[2]).toHaveAttribute("alt", "test-3.jpg");
  });

  it("shows upload spinner when uploading", () => {
    const attachments = [
      createMockPendingAttachment("1", { uploading: true }),
      createMockPendingAttachment("2", { uploading: false }),
    ];
    render(
      <AttachmentPreview attachments={attachments} onRemove={mockOnRemove} />,
    );

    // First attachment should have a spinner overlay (Loader2 icon with animate-spin)
    const container = screen.getByTestId("attachment-preview");
    const spinners = container.querySelectorAll(".animate-spin");
    expect(spinners).toHaveLength(1);
  });

  it("shows error overlay when error exists", () => {
    const attachments = [
      createMockPendingAttachment("1", { error: "Upload failed" }),
      createMockPendingAttachment("2"),
    ];
    render(
      <AttachmentPreview attachments={attachments} onRemove={mockOnRemove} />,
    );

    expect(screen.getByText("Error")).toBeInTheDocument();
  });

  it("calls onRemove with correct id when remove button clicked", async () => {
    const user = userEvent.setup();
    const attachments = [
      createMockPendingAttachment("1"),
      createMockPendingAttachment("2"),
      createMockPendingAttachment("3"),
    ];
    render(
      <AttachmentPreview attachments={attachments} onRemove={mockOnRemove} />,
    );

    const removeButton1 = screen.getByTestId("remove-attachment-1");
    const removeButton2 = screen.getByTestId("remove-attachment-2");

    await user.click(removeButton1);
    expect(mockOnRemove).toHaveBeenCalledWith("1");

    await user.click(removeButton2);
    expect(mockOnRemove).toHaveBeenCalledWith("2");
  });

  it("renders correct number of previews", () => {
    const attachments = [
      createMockPendingAttachment("1"),
      createMockPendingAttachment("2"),
      createMockPendingAttachment("3"),
      createMockPendingAttachment("4"),
      createMockPendingAttachment("5"),
    ];
    render(
      <AttachmentPreview attachments={attachments} onRemove={mockOnRemove} />,
    );

    const images = screen.getAllByRole("img");
    expect(images).toHaveLength(5);

    const removeButtons = screen.getAllByRole("button");
    expect(removeButtons).toHaveLength(5);
  });
});
