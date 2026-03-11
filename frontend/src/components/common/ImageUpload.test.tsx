import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";

import { ImageUpload } from "./ImageUpload";

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

describe("ImageUpload", () => {
  const defaultProps = {
    currentUrl: null,
    value: null,
    onChange: vi.fn(),
    label: "Logo",
  };

  it("renders upload placeholder when no image", () => {
    render(<ImageUpload {...defaultProps} />);

    expect(screen.getByText("Upload Logo")).toBeInTheDocument();
  });

  it("shows image when currentUrl is provided", () => {
    render(<ImageUpload {...defaultProps} currentUrl="https://example.com/logo.png" />);

    const img = screen.getByAltText("Logo");
    expect(img).toBeInTheDocument();
    expect(img).toHaveAttribute("src", "https://example.com/logo.png");
  });

  it("calls onChange(null) when remove is clicked", () => {
    const onChange = vi.fn();
    render(
      <ImageUpload
        {...defaultProps}
        currentUrl="https://example.com/logo.png"
        onChange={onChange}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /remove/i }));
    expect(onChange).toHaveBeenCalledWith(null);
  });

  it("shows correct label text", () => {
    render(<ImageUpload {...defaultProps} label="Banner" />);

    expect(screen.getByText("Banner")).toBeInTheDocument();
    expect(screen.getByText("Upload Banner")).toBeInTheDocument();
  });

  it("shows file size hint", () => {
    render(<ImageUpload {...defaultProps} />);

    expect(screen.getByText(/JPG, PNG, GIF or WebP\. Max 5 MB\./)).toBeInTheDocument();
  });

  it("shows custom max size in hint", () => {
    render(<ImageUpload {...defaultProps} maxSize={2 * 1024 * 1024} />);

    expect(screen.getByText(/Max 2 MB/)).toBeInTheDocument();
  });

  it("renders disabled state", () => {
    render(<ImageUpload {...defaultProps} disabled />);

    const uploadButton = screen.getByRole("button", { name: /upload logo/i });
    expect(uploadButton).toBeDisabled();
  });

  it("has a hidden file input with correct accept attribute", () => {
    render(<ImageUpload {...defaultProps} />);

    const input = screen.getByLabelText("Upload Logo");
    expect(input).toHaveAttribute("type", "file");
    expect(input).toHaveAttribute(
      "accept",
      "image/jpeg,image/png,image/gif,image/webp",
    );
  });

  it("calls onChange with file when valid file is selected", () => {
    const onChange = vi.fn();
    render(<ImageUpload {...defaultProps} onChange={onChange} />);

    const file = createFile("logo.png", 1024, "image/png");
    const input = screen.getByLabelText("Upload Logo");
    fireEvent.change(input, { target: { files: [file] } });

    expect(onChange).toHaveBeenCalledWith(file);
  });

  it("shows error toast for files exceeding max size", () => {
    const onChange = vi.fn();
    render(<ImageUpload {...defaultProps} onChange={onChange} />);

    const largeFile = createFile("large.png", 6 * 1024 * 1024, "image/png");
    const input = screen.getByLabelText("Upload Logo");
    fireEvent.change(input, { target: { files: [largeFile] } });

    expect(mockToastError).toHaveBeenCalledWith("Image must be smaller than 5 MB");
    expect(onChange).not.toHaveBeenCalled();
  });

  it("shows error toast for non-image files", () => {
    const onChange = vi.fn();
    render(<ImageUpload {...defaultProps} onChange={onChange} />);

    const textFile = createFile("doc.pdf", 1024, "application/pdf");
    const input = screen.getByLabelText("Upload Logo");
    fireEvent.change(input, { target: { files: [textFile] } });

    expect(mockToastError).toHaveBeenCalledWith(
      "Only JPEG, PNG, GIF, and WebP images are allowed",
    );
    expect(onChange).not.toHaveBeenCalled();
  });

  it("does not show remove/change overlay when disabled with image", () => {
    render(
      <ImageUpload
        {...defaultProps}
        currentUrl="https://example.com/logo.png"
        disabled
      />,
    );

    expect(screen.queryByRole("button", { name: /remove/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /change/i })).not.toBeInTheDocument();
  });

  it("shows remove and change buttons when image exists and not disabled", () => {
    render(
      <ImageUpload
        {...defaultProps}
        currentUrl="https://example.com/logo.png"
      />,
    );

    expect(screen.getByRole("button", { name: /remove/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /change/i })).toBeInTheDocument();
  });

  it("shows aspect hint when provided", () => {
    render(<ImageUpload {...defaultProps} aspectHint="1:1 recommended" />);

    expect(screen.getByText("1:1 recommended")).toBeInTheDocument();
  });

  it("disables file input when disabled", () => {
    render(<ImageUpload {...defaultProps} disabled />);

    const input = screen.getByLabelText("Upload Logo");
    expect(input).toBeDisabled();
  });
});
