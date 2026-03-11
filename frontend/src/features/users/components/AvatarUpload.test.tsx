import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const mockUploadMutateAsync = vi.fn();
const mockDeleteMutateAsync = vi.fn();

vi.mock("@/features/users/hooks/use-user-mutations", () => ({
  useUploadAvatar: vi.fn(() => ({
    mutateAsync: mockUploadMutateAsync,
    isPending: false,
  })),
  useDeleteAvatar: vi.fn(() => ({
    mutateAsync: mockDeleteMutateAsync,
    isPending: false,
  })),
}));

import { renderWithProviders } from "@/test/utils";

beforeEach(() => {
  vi.clearAllMocks();
});

describe("AvatarUpload", () => {
  async function renderComponent(props = {}) {
    const { AvatarUpload } = await import("./AvatarUpload");
    return renderWithProviders(
      <AvatarUpload
        avatarUrl={null}
        hasAvatar={false}
        fallbackText="J"
        {...props}
      />,
    );
  }

  it("renders avatar with fallback text", async () => {
    await renderComponent();

    expect(screen.getByText("J")).toBeInTheDocument();
  });

  it("shows Change Photo button", async () => {
    await renderComponent();

    expect(screen.getByRole("button", { name: /change photo/i })).toBeInTheDocument();
  });

  it("hides Remove button when no avatar", async () => {
    await renderComponent({ hasAvatar: false });

    expect(screen.queryByRole("button", { name: /remove/i })).not.toBeInTheDocument();
  });

  it("shows Remove button when has avatar", async () => {
    await renderComponent({ hasAvatar: true, avatarUrl: "https://example.com/avatar.jpg" });

    expect(screen.getByRole("button", { name: /remove/i })).toBeInTheDocument();
  });

  it("calls delete mutation on Remove click", async () => {
    const user = userEvent.setup();
    await renderComponent({ hasAvatar: true, avatarUrl: "https://example.com/avatar.jpg" });

    await user.click(screen.getByRole("button", { name: /remove/i }));
    expect(mockDeleteMutateAsync).toHaveBeenCalled();
  });

  it("has a hidden file input", async () => {
    await renderComponent();

    const input = screen.getByLabelText(/upload avatar/i);
    expect(input).toHaveAttribute("type", "file");
    expect(input).toHaveClass("hidden");
  });
});
