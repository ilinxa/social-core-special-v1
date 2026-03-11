import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";

import { FileUploadField } from "../components/form-builder/FileUploadField";

// Mock sonner toast
const mockToastError = vi.fn();
vi.mock("sonner", () => ({
  toast: {
    error: (...args: unknown[]) => mockToastError(...args),
  },
}));

// Mock URL.createObjectURL and revokeObjectURL for happy-dom
const mockCreateObjectURL = vi.fn(() => "blob:http://localhost/fake-url");
const mockRevokeObjectURL = vi.fn();
globalThis.URL.createObjectURL = mockCreateObjectURL;
globalThis.URL.revokeObjectURL = mockRevokeObjectURL;

beforeEach(() => {
  vi.clearAllMocks();
});

function createFile(name: string, size: number, type: string): File {
  const buffer = new ArrayBuffer(size);
  return new File([buffer], name, { type });
}

// =============================================================================
// FILE VARIANT
// =============================================================================

describe("FileUploadField — file variant", () => {
  const defaultProps = {
    variant: "file" as const,
    value: null as File | string | null,
    onChange: vi.fn(),
  };

  it("renders drop zone with upload prompt when no value", () => {
    render(<FileUploadField {...defaultProps} />);

    expect(screen.getByText("Click or drag to upload file")).toBeInTheDocument();
    expect(screen.getByText(/Max 10 MB/)).toBeInTheDocument();
  });

  it("shows file name and size when value is a File", () => {
    const file = createFile("report.pdf", 2048, "application/pdf");
    render(<FileUploadField {...defaultProps} value={file} />);

    expect(screen.getByText("report.pdf")).toBeInTheDocument();
    expect(screen.getByText("2.0 KB")).toBeInTheDocument();
  });

  it("shows file name extracted from URL when value is a string", () => {
    render(
      <FileUploadField
        {...defaultProps}
        value="https://example.com/uploads/document.pdf"
      />,
    );

    expect(screen.getByText("document.pdf")).toBeInTheDocument();
  });

  it("renders disabled state", () => {
    render(<FileUploadField {...defaultProps} disabled />);

    const uploadButton = screen.getByRole("button", {
      name: /click or drag to upload file/i,
    });
    expect(uploadButton).toBeDisabled();
  });

  it("hides change and remove buttons when disabled and has value", () => {
    const file = createFile("doc.pdf", 1024, "application/pdf");
    render(<FileUploadField {...defaultProps} value={file} disabled />);

    expect(screen.getByText("doc.pdf")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /change/i }),
    ).not.toBeInTheDocument();
  });

  it("shows change and remove buttons when has value and not disabled", () => {
    const file = createFile("doc.pdf", 1024, "application/pdf");
    render(<FileUploadField {...defaultProps} value={file} />);

    expect(screen.getByRole("button", { name: /change/i })).toBeInTheDocument();
    // Trash icon button exists (no text label, just icon)
    const buttons = screen.getAllByRole("button");
    expect(buttons.length).toBeGreaterThanOrEqual(2);
  });

  it("has a hidden file input", () => {
    render(<FileUploadField {...defaultProps} />);

    const input = screen.getByLabelText("Upload file");
    expect(input).toHaveAttribute("type", "file");
    expect(input).toHaveClass("hidden");
  });

  it("shows custom max size in hint", () => {
    render(
      <FileUploadField {...defaultProps} maxSize={5 * 1024 * 1024} />,
    );

    expect(screen.getByText(/Max 5 MB/)).toBeInTheDocument();
  });

  it("sets accept attribute from allowedTypes", () => {
    render(
      <FileUploadField
        {...defaultProps}
        allowedTypes={["application/pdf", "text/plain"]}
      />,
    );

    const input = screen.getByLabelText("Upload file");
    expect(input).toHaveAttribute("accept", "application/pdf,text/plain");
  });
});

// =============================================================================
// IMAGE VARIANT
// =============================================================================

describe("FileUploadField — image variant", () => {
  const defaultProps = {
    variant: "image" as const,
    value: null as File | string | null,
    onChange: vi.fn(),
  };

  it("renders drop zone with upload prompt when no value", () => {
    render(<FileUploadField {...defaultProps} />);

    expect(
      screen.getByText("Click or drag to upload image"),
    ).toBeInTheDocument();
    expect(screen.getByText(/JPEG, PNG, GIF or WebP/)).toBeInTheDocument();
    expect(screen.getByText(/Max 10 MB/)).toBeInTheDocument();
  });

  it("shows image preview when value is a File", () => {
    const file = createFile("photo.png", 2048, "image/png");
    render(<FileUploadField {...defaultProps} value={file} />);

    expect(mockCreateObjectURL).toHaveBeenCalledWith(file);
    const img = screen.getByAltText("Uploaded");
    expect(img).toBeInTheDocument();
    expect(img).toHaveAttribute("src", "blob:http://localhost/fake-url");
  });

  it("shows image preview when value is a URL string", () => {
    render(
      <FileUploadField
        {...defaultProps}
        value="https://example.com/image.png"
      />,
    );

    const img = screen.getByAltText("Uploaded");
    expect(img).toBeInTheDocument();
    expect(img).toHaveAttribute("src", "https://example.com/image.png");
  });

  it("shows change and remove overlay buttons when image exists", () => {
    render(
      <FileUploadField
        {...defaultProps}
        value="https://example.com/image.png"
      />,
    );

    expect(screen.getByRole("button", { name: /change/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /remove/i })).toBeInTheDocument();
  });

  it("does not show overlay buttons when disabled", () => {
    render(
      <FileUploadField
        {...defaultProps}
        value="https://example.com/image.png"
        disabled
      />,
    );

    expect(
      screen.queryByRole("button", { name: /change/i }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /remove/i }),
    ).not.toBeInTheDocument();
  });

  it("has a hidden file input with image accept types", () => {
    render(<FileUploadField {...defaultProps} />);

    const input = screen.getByLabelText("Upload image");
    expect(input).toHaveAttribute("type", "file");
    expect(input).toHaveAttribute(
      "accept",
      "image/jpeg,image/png,image/gif,image/webp",
    );
    expect(input).toHaveClass("hidden");
  });

  it("renders disabled state on drop zone button", () => {
    render(<FileUploadField {...defaultProps} disabled />);

    const uploadButton = screen.getByRole("button", {
      name: /click or drag to upload image/i,
    });
    expect(uploadButton).toBeDisabled();
  });

  it("cleans up object URL on unmount", () => {
    const file = createFile("photo.png", 2048, "image/png");
    const { unmount } = render(
      <FileUploadField {...defaultProps} value={file} />,
    );

    expect(mockCreateObjectURL).toHaveBeenCalled();
    unmount();
    expect(mockRevokeObjectURL).toHaveBeenCalledWith(
      "blob:http://localhost/fake-url",
    );
  });
});

// =============================================================================
// FILE SELECTION
// =============================================================================

describe("FileUploadField — file selection", () => {
  it("calls onChange with File when file input changes (file variant)", () => {
    const onChange = vi.fn();
    render(
      <FileUploadField variant="file" value={null} onChange={onChange} />,
    );

    const file = createFile("report.pdf", 1024, "application/pdf");
    const input = screen.getByLabelText("Upload file");
    fireEvent.change(input, { target: { files: [file] } });

    expect(onChange).toHaveBeenCalledWith(file);
  });

  it("calls onChange with File when file input changes (image variant)", () => {
    const onChange = vi.fn();
    render(
      <FileUploadField variant="image" value={null} onChange={onChange} />,
    );

    const file = createFile("photo.png", 1024, "image/png");
    const input = screen.getByLabelText("Upload image");
    fireEvent.change(input, { target: { files: [file] } });

    expect(onChange).toHaveBeenCalledWith(file);
  });

  it("does nothing if no file is selected", () => {
    const onChange = vi.fn();
    render(
      <FileUploadField variant="file" value={null} onChange={onChange} />,
    );

    const input = screen.getByLabelText("Upload file");
    fireEvent.change(input, { target: { files: [] } });

    expect(onChange).not.toHaveBeenCalled();
  });
});

// =============================================================================
// DRAG AND DROP
// =============================================================================

describe("FileUploadField — drag and drop", () => {
  it("calls onChange with file on drop (file variant)", () => {
    const onChange = vi.fn();
    render(
      <FileUploadField variant="file" value={null} onChange={onChange} />,
    );

    const dropZone = screen
      .getByText("Click or drag to upload file")
      .closest("div[class*='border-dashed']")!;

    const file = createFile("report.pdf", 1024, "application/pdf");
    fireEvent.drop(dropZone, {
      dataTransfer: { files: [file] },
    });

    expect(onChange).toHaveBeenCalledWith(file);
  });

  it("calls onChange with file on drop (image variant)", () => {
    const onChange = vi.fn();
    render(
      <FileUploadField variant="image" value={null} onChange={onChange} />,
    );

    const dropZone = screen
      .getByText("Click or drag to upload image")
      .closest("div[class*='border-dashed']")!;

    const file = createFile("photo.png", 1024, "image/png");
    fireEvent.drop(dropZone, {
      dataTransfer: { files: [file] },
    });

    expect(onChange).toHaveBeenCalledWith(file);
  });

  it("does not accept drop when disabled", () => {
    const onChange = vi.fn();
    render(
      <FileUploadField variant="file" value={null} onChange={onChange} disabled />,
    );

    const dropZone = screen
      .getByText("Click or drag to upload file")
      .closest("div[class*='border-dashed']")!;

    const file = createFile("report.pdf", 1024, "application/pdf");
    fireEvent.drop(dropZone, {
      dataTransfer: { files: [file] },
    });

    expect(onChange).not.toHaveBeenCalled();
  });

  it("prevents default on dragOver", () => {
    render(
      <FileUploadField variant="file" value={null} onChange={vi.fn()} />,
    );

    const dropZone = screen
      .getByText("Click or drag to upload file")
      .closest("div[class*='border-dashed']")!;

    const dragOverEvent = new Event("dragover", { bubbles: true });
    Object.defineProperty(dragOverEvent, "preventDefault", {
      value: vi.fn(),
      writable: true,
    });

    dropZone.dispatchEvent(dragOverEvent);

    expect(
      (dragOverEvent.preventDefault as ReturnType<typeof vi.fn>),
    ).toHaveBeenCalled();
  });
});

// =============================================================================
// VALIDATION
// =============================================================================

describe("FileUploadField — validation", () => {
  it("rejects file exceeding maxSize via input", () => {
    const onChange = vi.fn();
    render(
      <FileUploadField
        variant="file"
        value={null}
        onChange={onChange}
        maxSize={1 * 1024 * 1024}
      />,
    );

    const largeFile = createFile("big.zip", 2 * 1024 * 1024, "application/zip");
    const input = screen.getByLabelText("Upload file");
    fireEvent.change(input, { target: { files: [largeFile] } });

    expect(mockToastError).toHaveBeenCalledWith("File must be smaller than 1 MB");
    expect(onChange).not.toHaveBeenCalled();
  });

  it("rejects file exceeding maxSize via drop", () => {
    const onChange = vi.fn();
    render(
      <FileUploadField
        variant="file"
        value={null}
        onChange={onChange}
        maxSize={1 * 1024 * 1024}
      />,
    );

    const dropZone = screen
      .getByText("Click or drag to upload file")
      .closest("div[class*='border-dashed']")!;

    const largeFile = createFile("big.zip", 2 * 1024 * 1024, "application/zip");
    fireEvent.drop(dropZone, {
      dataTransfer: { files: [largeFile] },
    });

    expect(mockToastError).toHaveBeenCalledWith("File must be smaller than 1 MB");
    expect(onChange).not.toHaveBeenCalled();
  });

  it("rejects non-image file in image variant via input", () => {
    const onChange = vi.fn();
    render(
      <FileUploadField variant="image" value={null} onChange={onChange} />,
    );

    const textFile = createFile("doc.txt", 1024, "text/plain");
    const input = screen.getByLabelText("Upload image");
    fireEvent.change(input, { target: { files: [textFile] } });

    expect(mockToastError).toHaveBeenCalledWith(
      "Please select an image file (JPEG, PNG, GIF, or WebP)",
    );
    expect(onChange).not.toHaveBeenCalled();
  });

  it("rejects non-image file in image variant via drop", () => {
    const onChange = vi.fn();
    render(
      <FileUploadField variant="image" value={null} onChange={onChange} />,
    );

    const dropZone = screen
      .getByText("Click or drag to upload image")
      .closest("div[class*='border-dashed']")!;

    const textFile = createFile("doc.txt", 1024, "text/plain");
    fireEvent.drop(dropZone, {
      dataTransfer: { files: [textFile] },
    });

    expect(mockToastError).toHaveBeenCalledWith(
      "Please select an image file",
    );
    expect(onChange).not.toHaveBeenCalled();
  });

  it("rejects file with disallowed type when allowedTypes is set", () => {
    const onChange = vi.fn();
    render(
      <FileUploadField
        variant="file"
        value={null}
        onChange={onChange}
        allowedTypes={["application/pdf"]}
      />,
    );

    const zipFile = createFile("archive.zip", 1024, "application/zip");
    const input = screen.getByLabelText("Upload file");
    fireEvent.change(input, { target: { files: [zipFile] } });

    expect(mockToastError).toHaveBeenCalledWith(
      "File type application/zip is not allowed",
    );
    expect(onChange).not.toHaveBeenCalled();
  });

  it("accepts file with allowed type", () => {
    const onChange = vi.fn();
    render(
      <FileUploadField
        variant="file"
        value={null}
        onChange={onChange}
        allowedTypes={["application/pdf"]}
      />,
    );

    const pdfFile = createFile("report.pdf", 1024, "application/pdf");
    const input = screen.getByLabelText("Upload file");
    fireEvent.change(input, { target: { files: [pdfFile] } });

    expect(onChange).toHaveBeenCalledWith(pdfFile);
    expect(mockToastError).not.toHaveBeenCalled();
  });
});

// =============================================================================
// REMOVE
// =============================================================================

describe("FileUploadField — remove", () => {
  it("remove button calls onChange(null) in file variant", () => {
    const onChange = vi.fn();
    const file = createFile("doc.pdf", 1024, "application/pdf");
    render(
      <FileUploadField variant="file" value={file} onChange={onChange} />,
    );

    // The trash icon button is the second button (after Change)
    const buttons = screen.getAllByRole("button");
    // Find the button that contains the trash icon (last button)
    const removeButton = buttons[buttons.length - 1];
    fireEvent.click(removeButton);

    expect(onChange).toHaveBeenCalledWith(null);
  });

  it("image overlay Remove button calls onChange(null)", () => {
    const onChange = vi.fn();
    render(
      <FileUploadField
        variant="image"
        value="https://example.com/photo.png"
        onChange={onChange}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /remove/i }));

    expect(onChange).toHaveBeenCalledWith(null);
  });
});

// =============================================================================
// FORMAT FILE SIZE (indirectly tested through rendered output)
// =============================================================================

describe("FileUploadField — file size formatting", () => {
  it("formats bytes correctly", () => {
    const file = createFile("tiny.txt", 512, "text/plain");
    render(
      <FileUploadField variant="file" value={file} onChange={vi.fn()} />,
    );

    expect(screen.getByText("512 B")).toBeInTheDocument();
  });

  it("formats kilobytes correctly", () => {
    const file = createFile("small.txt", 5120, "text/plain");
    render(
      <FileUploadField variant="file" value={file} onChange={vi.fn()} />,
    );

    expect(screen.getByText("5.0 KB")).toBeInTheDocument();
  });

  it("formats megabytes correctly", () => {
    const file = createFile("medium.zip", 3 * 1024 * 1024, "application/zip");
    render(
      <FileUploadField variant="file" value={file} onChange={vi.fn()} />,
    );

    expect(screen.getByText("3.0 MB")).toBeInTheDocument();
  });
});
