import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AttachmentGrid } from "../AttachmentGrid";
import type { ChatAttachment } from "@/features/chat/types";

const createMockAttachment = (id: string): ChatAttachment => ({
  id,
  file_type: "image",
  original_filename: `image-${id}.jpg`,
  mime_type: "image/jpeg",
  file_size: 1024,
  width: 800,
  height: 600,
  url: `https://example.com/image-${id}.jpg`,
});

describe("AttachmentGrid", () => {
  it("returns null for empty attachments", () => {
    const { container } = render(<AttachmentGrid attachments={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders single image with full width class", () => {
    const attachments = [createMockAttachment("1")];
    render(<AttachmentGrid attachments={attachments} />);

    const grid = screen.getByTestId("attachment-grid");
    expect(grid).toHaveClass("grid-cols-1");

    const image = screen.getByTestId("attachment-0");
    expect(image).toBeInTheDocument();
  });

  it("renders 2 images side by side (grid-cols-2)", () => {
    const attachments = [createMockAttachment("1"), createMockAttachment("2")];
    render(<AttachmentGrid attachments={attachments} />);

    const grid = screen.getByTestId("attachment-grid");
    expect(grid).toHaveClass("grid-cols-2");

    const image1 = screen.getByTestId("attachment-0");
    const image2 = screen.getByTestId("attachment-1");
    expect(image1).toBeInTheDocument();
    expect(image2).toBeInTheDocument();
  });

  it("renders 3-4 images in 2x2 grid", () => {
    const attachments = [
      createMockAttachment("1"),
      createMockAttachment("2"),
      createMockAttachment("3"),
      createMockAttachment("4"),
    ];
    render(<AttachmentGrid attachments={attachments} />);

    const grid = screen.getByTestId("attachment-grid");
    expect(grid).toHaveClass("grid-cols-2");

    const image1 = screen.getByTestId("attachment-0");
    const image2 = screen.getByTestId("attachment-1");
    const image3 = screen.getByTestId("attachment-2");
    const image4 = screen.getByTestId("attachment-3");
    expect(image1).toBeInTheDocument();
    expect(image2).toBeInTheDocument();
    expect(image3).toBeInTheDocument();
    expect(image4).toBeInTheDocument();
  });

  it("shows +N overlay when more than 4 images", () => {
    const attachments = [
      createMockAttachment("1"),
      createMockAttachment("2"),
      createMockAttachment("3"),
      createMockAttachment("4"),
      createMockAttachment("5"),
      createMockAttachment("6"),
    ];
    render(<AttachmentGrid attachments={attachments} />);

    // Should only render first 4 images
    expect(screen.getByTestId("attachment-0")).toBeInTheDocument();
    expect(screen.getByTestId("attachment-1")).toBeInTheDocument();
    expect(screen.getByTestId("attachment-2")).toBeInTheDocument();
    expect(screen.getByTestId("attachment-3")).toBeInTheDocument();
    expect(screen.queryByTestId("attachment-4")).not.toBeInTheDocument();

    // Check for +2 overlay (6 - 4 = 2)
    expect(screen.getByText("+2")).toBeInTheDocument();
  });

  it("calls onImageClick with correct index on click", async () => {
    const user = userEvent.setup();
    const onImageClick = vi.fn();
    const attachments = [
      createMockAttachment("1"),
      createMockAttachment("2"),
      createMockAttachment("3"),
    ];
    render(
      <AttachmentGrid attachments={attachments} onImageClick={onImageClick} />,
    );

    const image1 = screen.getByTestId("attachment-0");
    const image2 = screen.getByTestId("attachment-1");

    await user.click(image1);
    expect(onImageClick).toHaveBeenCalledWith(0);

    await user.click(image2);
    expect(onImageClick).toHaveBeenCalledWith(1);
  });

  it("images have lazy loading attribute", () => {
    const attachments = [
      createMockAttachment("1"),
      createMockAttachment("2"),
    ];
    render(<AttachmentGrid attachments={attachments} />);

    const images = screen.getAllByRole("img");
    images.forEach((img) => {
      expect(img).toHaveAttribute("loading", "lazy");
    });
  });
});
