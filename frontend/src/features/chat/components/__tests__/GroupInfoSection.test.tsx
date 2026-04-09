import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { GroupInfoSection } from "../GroupInfoSection";

const mockMutate = vi.fn();
vi.mock("@/features/chat/hooks/use-chat-mutations", () => ({
  useUpdateConversation: () => ({ mutate: mockMutate, isPending: false }),
}));

describe("GroupInfoSection", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders group name in view mode", () => {
    render(
      <GroupInfoSection
        conversationId="conv-1"
        name="Engineering Team"
        description="Team chat"
        canEdit={false}
      />
    );

    expect(screen.getByTestId("group-info-section")).toBeInTheDocument();
    expect(screen.getByText("Engineering Team")).toBeInTheDocument();
  });

  it("renders description in view mode", () => {
    render(
      <GroupInfoSection
        conversationId="conv-1"
        name="Engineering Team"
        description="Team chat for engineering discussions"
        canEdit={false}
      />
    );

    expect(
      screen.getByText("Team chat for engineering discussions")
    ).toBeInTheDocument();
  });

  it("shows edit button when canEdit is true", () => {
    render(
      <GroupInfoSection
        conversationId="conv-1"
        name="Engineering Team"
        description="Team chat"
        canEdit={true}
      />
    );

    expect(
      screen.getByTestId("edit-group-info-button")
    ).toBeInTheDocument();
  });

  it("hides edit button when canEdit is false", () => {
    render(
      <GroupInfoSection
        conversationId="conv-1"
        name="Engineering Team"
        description="Team chat"
        canEdit={false}
      />
    );

    expect(
      screen.queryByTestId("edit-group-info-button")
    ).not.toBeInTheDocument();
  });

  it("clicking edit switches to edit mode", async () => {
    const user = userEvent.setup();
    render(
      <GroupInfoSection
        conversationId="conv-1"
        name="Engineering Team"
        description="Team chat"
        canEdit={true}
      />
    );

    await user.click(screen.getByTestId("edit-group-info-button"));

    expect(screen.getByTestId("group-info-edit")).toBeInTheDocument();
  });

  it("cancel reverts to view mode", async () => {
    const user = userEvent.setup();
    render(
      <GroupInfoSection
        conversationId="conv-1"
        name="Engineering Team"
        description="Team chat"
        canEdit={true}
      />
    );

    await user.click(screen.getByTestId("edit-group-info-button"));
    expect(screen.getByTestId("group-info-edit")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /cancel/i }));
    expect(screen.getByTestId("group-info-section")).toBeInTheDocument();
    expect(screen.queryByTestId("group-info-edit")).not.toBeInTheDocument();
  });

  it("save button disabled when name is empty", async () => {
    const user = userEvent.setup();
    render(
      <GroupInfoSection
        conversationId="conv-1"
        name="Engineering Team"
        description="Team chat"
        canEdit={true}
      />
    );

    await user.click(screen.getByTestId("edit-group-info-button"));

    const nameInput = screen.getAllByRole("textbox")[0];
    await user.clear(nameInput);

    const saveButton = screen.getByRole("button", { name: /save/i });
    expect(saveButton).toBeDisabled();
  });

  it("save calls mutate with changed fields", async () => {
    const user = userEvent.setup();
    render(
      <GroupInfoSection
        conversationId="conv-1"
        name="Engineering Team"
        description="Team chat"
        canEdit={true}
      />
    );

    await user.click(screen.getByTestId("edit-group-info-button"));

    const nameInput = screen.getAllByRole("textbox")[0];
    await user.clear(nameInput);
    await user.type(nameInput, "New Team Name");

    const descriptionInput = screen.getAllByRole("textbox")[1];
    await user.clear(descriptionInput);
    await user.type(descriptionInput, "Updated description");

    await user.click(screen.getByRole("button", { name: /save/i }));

    expect(mockMutate).toHaveBeenCalledWith(
      { name: "New Team Name", description: "Updated description" },
      expect.objectContaining({ onSuccess: expect.any(Function) }),
    );
  });
});
