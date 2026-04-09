import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AttachmentButton } from "../AttachmentButton";
import { toast } from "sonner";

vi.mock("sonner", () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}));

describe("AttachmentButton", () => {
  const mockOnFilesSelected = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders attachment button", () => {
    render(
      <AttachmentButton onFilesSelected={mockOnFilesSelected} currentCount={0} />,
    );

    const button = screen.getByTestId("attachment-button");
    expect(button).toBeInTheDocument();
    expect(button).not.toBeDisabled();
  });

  it("button is disabled when disabled prop is true", () => {
    render(
      <AttachmentButton
        onFilesSelected={mockOnFilesSelected}
        currentCount={0}
        disabled={true}
      />,
    );

    const button = screen.getByTestId("attachment-button");
    expect(button).toBeDisabled();
  });

  it("button is disabled when currentCount >= 10", () => {
    render(
      <AttachmentButton onFilesSelected={mockOnFilesSelected} currentCount={10} />,
    );

    const button = screen.getByTestId("attachment-button");
    expect(button).toBeDisabled();
  });

  it("calls onFilesSelected with valid files", async () => {
    const user = userEvent.setup();
    render(
      <AttachmentButton onFilesSelected={mockOnFilesSelected} currentCount={0} />,
    );

    const input = screen.getByTestId("attachment-file-input");
    const file1 = new File(["test1"], "test1.jpg", { type: "image/jpeg" });
    const file2 = new File(["test2"], "test2.png", { type: "image/png" });

    await user.upload(input, [file1, file2]);

    expect(mockOnFilesSelected).toHaveBeenCalledWith([file1, file2]);
  });

  it("shows toast error for invalid file type", async () => {
    // Disable accept filtering so the invalid file reaches the onChange handler
    const user = userEvent.setup({ applyAccept: false });
    render(
      <AttachmentButton onFilesSelected={mockOnFilesSelected} currentCount={0} />,
    );

    const input = screen.getByTestId("attachment-file-input");
    const invalidFile = new File(["test"], "test.pdf", {
      type: "application/pdf",
    });

    await user.upload(input, invalidFile);

    expect(toast.error).toHaveBeenCalledWith(
      "test.pdf: Unsupported file type. Use JPEG, PNG, GIF, or WebP.",
    );
    expect(mockOnFilesSelected).not.toHaveBeenCalled();
  });

  it("shows toast error for file too large", async () => {
    const user = userEvent.setup();
    render(
      <AttachmentButton onFilesSelected={mockOnFilesSelected} currentCount={0} />,
    );

    const input = screen.getByTestId("attachment-file-input");
    // Create a file larger than 10MB
    const largeContent = new Array(11 * 1024 * 1024).fill("a").join("");
    const largeFile = new File([largeContent], "large.jpg", {
      type: "image/jpeg",
    });

    // Mock the file size property
    Object.defineProperty(largeFile, "size", {
      value: 11 * 1024 * 1024,
      writable: false,
    });

    await user.upload(input, largeFile);

    expect(toast.error).toHaveBeenCalledWith(
      "large.jpg: File too large. Maximum 10 MB.",
    );
    expect(mockOnFilesSelected).not.toHaveBeenCalled();
  });

  it("limits files to remaining count (10 - currentCount)", async () => {
    const user = userEvent.setup();
    render(
      <AttachmentButton onFilesSelected={mockOnFilesSelected} currentCount={8} />,
    );

    const input = screen.getByTestId("attachment-file-input");
    const files = [
      new File(["test1"], "test1.jpg", { type: "image/jpeg" }),
      new File(["test2"], "test2.jpg", { type: "image/jpeg" }),
      new File(["test3"], "test3.jpg", { type: "image/jpeg" }),
      new File(["test4"], "test4.jpg", { type: "image/jpeg" }),
    ];

    await user.upload(input, files);

    // Should only call with first 2 files (8 + 2 = 10 max)
    expect(mockOnFilesSelected).toHaveBeenCalledWith([files[0], files[1]]);
  });
});
