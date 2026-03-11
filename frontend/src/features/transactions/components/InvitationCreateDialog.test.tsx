import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";

const mockMutate = vi.hoisted(() => vi.fn());

vi.mock("@/features/explore/api/explore-api", () => ({
  searchUsersApi: vi.fn(),
}));

vi.mock("@/features/members/api/members-api", () => ({
  fetchMembersApi: vi.fn(),
}));

vi.mock("@/features/transactions/api/transactions-api", () => ({
  fetchTransactionsApi: vi.fn(),
}));

vi.mock("@/features/members/hooks/use-role-queries", () => ({
  useRoleList: () => ({
    data: [
      { id: "role-1", name: "Admin", level: 2, is_system_role: true, description: "", member_count: 1, created_at: "", updated_at: "", account_type: "business", account_id: "biz-1" },
      { id: "role-2", name: "Base Member", level: 10, is_system_role: true, description: "", member_count: 3, created_at: "", updated_at: "", account_type: "business", account_id: "biz-1" },
    ],
  }),
}));

vi.mock("@/features/transactions/hooks/use-transaction-mutations", () => ({
  useCreateInvitation: () => ({
    mutate: mockMutate,
    isPending: false,
  }),
}));

import { searchUsersApi } from "@/features/explore/api/explore-api";
import { fetchMembersApi } from "@/features/members/api/members-api";
import { fetchTransactionsApi } from "@/features/transactions/api/transactions-api";
import { InvitationCreateDialog } from "./InvitationCreateDialog";

const mockSearchUsers = vi.mocked(searchUsersApi);
const mockFetchMembers = vi.mocked(fetchMembersApi);
const mockFetchTransactions = vi.mocked(fetchTransactionsApi);

const PLACEHOLDER = "Search by name, username, or email...";

const defaultProps = {
  open: true,
  onOpenChange: vi.fn(),
  accountType: "business" as const,
  accountId: "biz-123",
  slug: "test-biz",
  actorRoleLevel: 0,
};

function makeUser(overrides: Record<string, unknown> = {}) {
  return {
    id: "user-1",
    username: "johndoe",
    email: "john@example.com",
    display_name: "John Doe",
    is_verified: false,
    profile: { first_name: "John", last_name: "Doe", bio: "", avatar_url: null, country: "", city: "", tags: [] },
    search_rank: 1,
    ...overrides,
  };
}

function emptyPaginatedResponse() {
  return { results: [], count: 0, next: null, previous: null };
}

describe("InvitationCreateDialog", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Default: no existing members, no pending transactions
    mockFetchMembers.mockResolvedValue({ results: [], count: 0, next: null, previous: null });
    mockFetchTransactions.mockResolvedValue(emptyPaginatedResponse());
  });

  it("renders the dialog with search input", () => {
    render(<InvitationCreateDialog {...defaultProps} />);
    expect(screen.getByText("Invite Member")).toBeInTheDocument();
    expect(screen.getByPlaceholderText(PLACEHOLDER)).toBeInTheDocument();
    expect(screen.getByText("Type at least 2 characters to search.")).toBeInTheDocument();
  });

  it("searches for users automatically as you type (debounced)", async () => {
    const user = userEvent.setup();
    mockSearchUsers.mockResolvedValue({
      results: [makeUser(), makeUser({ id: "user-2", username: "janedoe", display_name: "Jane Doe" })],
      count: 2,
      next: null,
      previous: null,
    });

    render(<InvitationCreateDialog {...defaultProps} />);

    await user.type(screen.getByPlaceholderText(PLACEHOLDER), "doe");

    await waitFor(() => {
      expect(screen.getByText("John Doe")).toBeInTheDocument();
      expect(screen.getByText("Jane Doe")).toBeInTheDocument();
    });
  });

  it("shows empty state when no users found", async () => {
    const user = userEvent.setup();
    mockSearchUsers.mockResolvedValue(emptyPaginatedResponse());

    render(<InvitationCreateDialog {...defaultProps} />);

    await user.type(screen.getByPlaceholderText(PLACEHOLDER), "nonexistent");

    await waitFor(() => {
      expect(screen.getByText("No users found. Try a different search term.")).toBeInTheDocument();
    });
  });

  it("does not search when less than 2 characters typed", async () => {
    const user = userEvent.setup();

    render(<InvitationCreateDialog {...defaultProps} />);

    await user.type(screen.getByPlaceholderText(PLACEHOLDER), "j");

    // Wait a bit to ensure debounce fires
    await new Promise((r) => setTimeout(r, 400));

    expect(mockSearchUsers).not.toHaveBeenCalled();
    expect(screen.getByText("Type at least 2 characters to search.")).toBeInTheDocument();
  });

  it("advances to configure step when user is selected", async () => {
    const user = userEvent.setup();
    mockSearchUsers.mockResolvedValue({
      results: [makeUser()],
      count: 1,
      next: null,
      previous: null,
    });

    render(<InvitationCreateDialog {...defaultProps} />);

    await user.type(screen.getByPlaceholderText(PLACEHOLDER), "john");

    await waitFor(() => {
      expect(screen.getByText("John Doe")).toBeInTheDocument();
    });

    await user.click(screen.getByText("John Doe"));

    // Should be on configure step now
    expect(screen.getByText("Send Invitation")).toBeInTheDocument();
    expect(screen.getByText("Configure the invitation and send it.")).toBeInTheDocument();
    expect(screen.getByText("@johndoe")).toBeInTheDocument();
  });

  it("calls createInvitation with correct data on submit", async () => {
    const user = userEvent.setup();
    mockSearchUsers.mockResolvedValue({
      results: [makeUser()],
      count: 1,
      next: null,
      previous: null,
    });

    render(<InvitationCreateDialog {...defaultProps} />);

    await user.type(screen.getByPlaceholderText(PLACEHOLDER), "john");

    await waitFor(() => {
      expect(screen.getByText("John Doe")).toBeInTheDocument();
    });

    await user.click(screen.getByText("John Doe"));
    await user.click(screen.getByText("Send Invitation"));

    expect(mockMutate).toHaveBeenCalledWith(
      {
        transaction_type: "business_membership_invitation",
        target_user_id: "user-1",
        context_type: "business",
        context_id: "biz-123",
        payload: { role_id: "role-2" },
      },
      expect.objectContaining({
        onSuccess: expect.any(Function),
        onError: expect.any(Function),
      }),
    );
  });

  it("navigates back from configure to search step", async () => {
    const user = userEvent.setup();
    mockSearchUsers.mockResolvedValue({
      results: [makeUser()],
      count: 1,
      next: null,
      previous: null,
    });

    render(<InvitationCreateDialog {...defaultProps} />);

    await user.type(screen.getByPlaceholderText(PLACEHOLDER), "john");

    await waitFor(() => {
      expect(screen.getByText("John Doe")).toBeInTheDocument();
    });

    await user.click(screen.getByText("John Doe"));
    expect(screen.getByText("Send Invitation")).toBeInTheDocument();

    await user.click(screen.getByText("Back"));
    expect(screen.getByPlaceholderText(PLACEHOLDER)).toBeInTheDocument();
  });

  it("uses platform transaction type for platform accounts", async () => {
    const user = userEvent.setup();
    mockSearchUsers.mockResolvedValue({
      results: [makeUser()],
      count: 1,
      next: null,
      previous: null,
    });

    render(
      <InvitationCreateDialog
        {...defaultProps}
        accountType="platform"
        slug="platform"
      />,
    );

    await user.type(screen.getByPlaceholderText(PLACEHOLDER), "john");

    await waitFor(() => {
      expect(screen.getByText("John Doe")).toBeInTheDocument();
    });

    await user.click(screen.getByText("John Doe"));
    await user.click(screen.getByText("Send Invitation"));

    expect(mockMutate).toHaveBeenCalledWith(
      expect.objectContaining({
        transaction_type: "platform_membership_invitation",
        context_type: "platform",
      }),
      expect.anything(),
    );
  });

  // =========================================================================
  // MEMBER FILTERING TESTS
  // =========================================================================

  it("marks existing members as unselectable", async () => {
    const user = userEvent.setup();
    // User-1 is already a member
    mockFetchMembers.mockResolvedValue({
      results: [{ user: { id: "user-1" } }] as never,
      count: 1,
      next: null,
      previous: null,
    });
    mockSearchUsers.mockResolvedValue({
      results: [
        makeUser(),
        makeUser({ id: "user-2", username: "janedoe", display_name: "Jane Doe" }),
      ],
      count: 2,
      next: null,
      previous: null,
    });

    render(<InvitationCreateDialog {...defaultProps} />);

    await user.type(screen.getByPlaceholderText(PLACEHOLDER), "doe");

    await waitFor(() => {
      expect(screen.getByText("John Doe")).toBeInTheDocument();
      expect(screen.getByText("Jane Doe")).toBeInTheDocument();
    });

    // John should have "Member" badge and be disabled
    expect(screen.getByText("Member")).toBeInTheDocument();

    // Jane should be clickable
    await user.click(screen.getByText("Jane Doe"));
    expect(screen.getByText("Send Invitation")).toBeInTheDocument();
  });

  // =========================================================================
  // QUOTA TESTS
  // =========================================================================

  it("shows quota warning when member limit reached", async () => {
    // 3 active members + 2 pending = 5 total, maxMembers = 5
    mockFetchMembers.mockResolvedValue({
      results: Array.from({ length: 3 }, (_, i) => ({ user: { id: `m-${i}` } })) as never,
      count: 3,
      next: null,
      previous: null,
    });
    mockFetchTransactions.mockResolvedValue({
      results: [{}] as never,
      count: 1,
      next: null,
      previous: null,
    });

    render(<InvitationCreateDialog {...defaultProps} maxMembers={5} />);

    await waitFor(() => {
      expect(screen.getByText(/Member quota reached/)).toBeInTheDocument();
    });

    // Search input should be disabled
    expect(screen.getByPlaceholderText(PLACEHOLDER)).toBeDisabled();
  });

  it("allows search when quota is not full", async () => {
    // 2 active members + 0 pending = 2, maxMembers = 10
    mockFetchMembers.mockResolvedValue({
      results: [{ user: { id: "m-1" } }, { user: { id: "m-2" } }] as never,
      count: 2,
      next: null,
      previous: null,
    });

    render(<InvitationCreateDialog {...defaultProps} maxMembers={10} />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText(PLACEHOLDER)).not.toBeDisabled();
    });

    expect(screen.queryByText(/Member quota reached/)).not.toBeInTheDocument();
  });

  it("treats maxMembers=0 as unlimited", async () => {
    mockFetchMembers.mockResolvedValue({
      results: Array.from({ length: 50 }, (_, i) => ({ user: { id: `m-${i}` } })) as never,
      count: 50,
      next: null,
      previous: null,
    });

    render(<InvitationCreateDialog {...defaultProps} maxMembers={0} />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText(PLACEHOLDER)).not.toBeDisabled();
    });

    expect(screen.queryByText(/Member quota reached/)).not.toBeInTheDocument();
  });
});
