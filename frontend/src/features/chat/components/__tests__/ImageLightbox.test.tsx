import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ImageLightbox } from "../ImageLightbox";
import type { ChatAttachment } from "../../types";

describe("ImageLightbox", () => {
  const mockOnOpenChange = vi.fn();

  const singleAttachment: ChatAttachment[] = [
    {
      id: "att-1",
      file_type: "image",
      original_filename: "photo1.jpg",
      mime_type: "image/jpeg",
      file_size: 102400,
      width: 1920,
      height: 1080,
      url: "https://example.com/photo1.jpg",
    },
  ];

  const multipleAttachments: ChatAttachment[] = [
    {
      id: "att-1",
      file_type: "image",
      original_filename: "photo1.jpg",
      mime_type: "image/jpeg",
      file_size: 102400,
      width: 1920,
      height: 1080,
      url: "https://example.com/photo1.jpg",
    },
    {
      id: "att-2",
      file_type: "image",
      original_filename: "photo2.jpg",
      mime_type: "image/jpeg",
      file_size: 204800,
      width: 1920,
      height: 1080,
      url: "https://example.com/photo2.jpg",
    },
    {
      id: "att-3",
      file_type: "image",
      original_filename: "photo3.jpg",
      mime_type: "image/jpeg",
      file_size: 307200,
      width: 1920,
      height: 1080,
      url: "https://example.com/photo3.jpg",
    },
  ];

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("renders current image", () => {
    render(
      <ImageLightbox
        attachments={singleAttachment}
        initialIndex={0}
        open={true}
        onOpenChange={mockOnOpenChange}
      />
    );

    expect(screen.getByTestId("image-lightbox")).toBeInTheDocument();
    const image = screen.getByRole("img");
    expect(image).toHaveAttribute("src", "https://example.com/photo1.jpg");
    expect(image).toHaveAttribute("alt", "photo1.jpg");
  });

  it("shows counter for multiple images", () => {
    render(
      <ImageLightbox
        attachments={multipleAttachments}
        initialIndex={0}
        open={true}
        onOpenChange={mockOnOpenChange}
      />
    );

    expect(screen.getByText("1 / 3")).toBeInTheDocument();
  });

  it("hides counter for single image", () => {
    render(
      <ImageLightbox
        attachments={singleAttachment}
        initialIndex={0}
        open={true}
        onOpenChange={mockOnOpenChange}
      />
    );

    expect(screen.queryByText(/\/ 1/)).not.toBeInTheDocument();
  });

  it("navigates to next image", async () => {
    const user = userEvent.setup();
    render(
      <ImageLightbox
        attachments={multipleAttachments}
        initialIndex={0}
        open={true}
        onOpenChange={mockOnOpenChange}
      />
    );

    await user.keyboard("{ArrowRight}");

    const image = screen.getByRole("img");
    expect(image).toHaveAttribute("src", "https://example.com/photo2.jpg");
    expect(screen.getByText("2 / 3")).toBeInTheDocument();
  });

  it("navigates to previous image", async () => {
    const user = userEvent.setup();
    render(
      <ImageLightbox
        attachments={multipleAttachments}
        initialIndex={1}
        open={true}
        onOpenChange={mockOnOpenChange}
      />
    );

    await user.keyboard("{ArrowLeft}");

    const image = screen.getByRole("img");
    expect(image).toHaveAttribute("src", "https://example.com/photo1.jpg");
    expect(screen.getByText("1 / 3")).toBeInTheDocument();
  });

  it("keyboard ArrowRight navigates forward", async () => {
    const user = userEvent.setup();
    render(
      <ImageLightbox
        attachments={multipleAttachments}
        initialIndex={0}
        open={true}
        onOpenChange={mockOnOpenChange}
      />
    );

    await user.keyboard("{ArrowRight}");

    const image = screen.getByRole("img");
    expect(image).toHaveAttribute("src", "https://example.com/photo2.jpg");
    expect(screen.getByText("2 / 3")).toBeInTheDocument();
  });

  it("renders lightbox container when open", () => {
    render(
      <ImageLightbox
        attachments={singleAttachment}
        initialIndex={0}
        open={true}
        onOpenChange={mockOnOpenChange}
      />
    );

    expect(screen.getByTestId("image-lightbox")).toBeInTheDocument();
  });
});
