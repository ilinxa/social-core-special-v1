"use client";

import { useCallback, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { useUpdateConversation } from "@/features/chat/hooks/use-chat-mutations";

interface GroupInfoSectionProps {
  conversationId: string;
  name: string;
  description: string;
  canEdit: boolean;
}

/**
 * Edit group name and description section.
 * Only editable when user has can_edit_group permission.
 */
export function GroupInfoSection({
  conversationId,
  name,
  description,
  canEdit,
}: GroupInfoSectionProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editName, setEditName] = useState(name);
  const [editDescription, setEditDescription] = useState(description);
  const update = useUpdateConversation(conversationId);

  const handleSave = useCallback(() => {
    const changes: Record<string, string> = {};
    if (editName.trim() !== name) changes.name = editName.trim();
    if (editDescription.trim() !== description)
      changes.description = editDescription.trim();

    if (Object.keys(changes).length === 0) {
      setIsEditing(false);
      return;
    }

    update.mutate(changes, {
      onSuccess: () => setIsEditing(false),
    });
  }, [editName, editDescription, name, description, update]);

  const handleCancel = () => {
    setEditName(name);
    setEditDescription(description);
    setIsEditing(false);
  };

  if (!isEditing) {
    return (
      <div className="space-y-2 px-3" data-testid="group-info-section">
        <div>
          <p className="text-xs font-medium text-muted-foreground">Name</p>
          <p className="text-sm">{name}</p>
        </div>
        {description && (
          <div>
            <p className="text-xs font-medium text-muted-foreground">
              Description
            </p>
            <p className="text-sm text-muted-foreground">{description}</p>
          </div>
        )}
        {canEdit && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsEditing(true)}
            data-testid="edit-group-info-button"
          >
            Edit
          </Button>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-3 px-3" data-testid="group-info-edit">
      <div>
        <label className="text-xs font-medium text-muted-foreground">
          Name
        </label>
        <Input
          value={editName}
          onChange={(e) => setEditName(e.target.value)}
          className="mt-1"
          maxLength={100}
        />
      </div>
      <div>
        <label className="text-xs font-medium text-muted-foreground">
          Description
        </label>
        <Textarea
          value={editDescription}
          onChange={(e) => setEditDescription(e.target.value)}
          className="mt-1"
          rows={2}
          maxLength={500}
        />
      </div>
      <div className="flex gap-2">
        <Button
          size="sm"
          onClick={handleSave}
          disabled={!editName.trim() || update.isPending}
        >
          Save
        </Button>
        <Button size="sm" variant="ghost" onClick={handleCancel}>
          Cancel
        </Button>
      </div>
    </div>
  );
}
