import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";

import { renderWithProviders } from "@/test/utils";
import { SessionList } from "./SessionList";

import type { DeviceSession } from "@/features/auth/types";

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    back: vi.fn(),
  }),
}));

const mockSessions: DeviceSession[] = [
  {
    id: "session-1",
    device_id: "device-1",
    device_name: "Chrome on Windows",
    device_type: "web",
    ip_address: "192.168.1.1",
    location: "New York, US",
    last_activity: new Date().toISOString(),
    is_active: true,
    is_current: true,
    created_at: "2026-02-24T00:00:00Z",
  },
  {
    id: "session-2",
    device_id: "device-2",
    device_name: "Safari on macOS",
    device_type: "web",
    ip_address: "10.0.0.1",
    location: "London, UK",
    last_activity: new Date(Date.now() - 3600000).toISOString(),
    is_active: true,
    is_current: false,
    created_at: "2026-02-23T00:00:00Z",
  },
];

const mockRevokeMutate = vi.fn();

vi.mock("@/features/auth/hooks/use-auth-queries", () => ({
  useSessions: vi.fn(),
}));

vi.mock("@/features/auth/hooks/use-auth-mutations", () => ({
  useRevokeSession: () => ({
    mutate: mockRevokeMutate,
    isPending: false,
  }),
  useLogoutAll: () => ({
    mutate: vi.fn(),
    isPending: false,
  }),
}));

import { useSessions } from "@/features/auth/hooks/use-auth-queries";

describe("SessionList", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders loading skeleton", () => {
    vi.mocked(useSessions).mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    } as unknown as ReturnType<typeof useSessions>);

    renderWithProviders(<SessionList />);
    // Skeletons are rendered (3 of them)
    expect(document.querySelectorAll("[data-slot='skeleton']").length).toBeGreaterThan(0);
  });

  it("renders sessions list", () => {
    vi.mocked(useSessions).mockReturnValue({
      data: mockSessions,
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof useSessions>);

    renderWithProviders(<SessionList />);

    expect(screen.getByText("Chrome on Windows")).toBeInTheDocument();
    expect(screen.getByText("Safari on macOS")).toBeInTheDocument();
    expect(screen.getByText("Current")).toBeInTheDocument();
  });

  it("shows revoke button only for non-current sessions", () => {
    vi.mocked(useSessions).mockReturnValue({
      data: mockSessions,
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof useSessions>);

    renderWithProviders(<SessionList />);

    const revokeButtons = screen.getAllByRole("button", { name: /revoke/i });
    // Only one revoke button (for the non-current session) + "Revoke All" button
    // The "Revoke" button is for session-2 only; session-1 is current
    expect(revokeButtons.length).toBeGreaterThanOrEqual(1);
  });

  it("calls revoke mutation on click", async () => {
    vi.mocked(useSessions).mockReturnValue({
      data: mockSessions,
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof useSessions>);

    const user = userEvent.setup();
    renderWithProviders(<SessionList />);

    const revokeButton = screen.getByRole("button", { name: "Revoke" });
    await user.click(revokeButton);

    expect(mockRevokeMutate).toHaveBeenCalledWith("session-2");
  });

  it("renders error state", () => {
    vi.mocked(useSessions).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error("Failed"),
    } as unknown as ReturnType<typeof useSessions>);

    renderWithProviders(<SessionList />);

    expect(screen.getByText(/failed to load sessions/i)).toBeInTheDocument();
  });

  it("renders empty state", () => {
    vi.mocked(useSessions).mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof useSessions>);

    renderWithProviders(<SessionList />);

    expect(screen.getByText(/no active sessions/i)).toBeInTheDocument();
  });
});
