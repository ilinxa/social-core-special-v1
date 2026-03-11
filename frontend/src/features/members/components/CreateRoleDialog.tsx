"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import type { CreateRoleInput } from "@/types/members";

interface CreateRoleDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  actorRoleLevel: number;
  onSubmit: (data: CreateRoleInput) => void;
  isLoading?: boolean;
}

export function CreateRoleDialog({
  open,
  onOpenChange,
  actorRoleLevel,
  onSubmit,
  isLoading,
}: CreateRoleDialogProps) {
  const [name, setName] = useState("");
  const [level, setLevel] = useState<string>("");
  const [description, setDescription] = useState("");

  const minLevel = actorRoleLevel + 1;
  const levelNum = parseInt(level, 10);
  const isValid = name.trim().length > 0 && !isNaN(levelNum) && levelNum >= minLevel;

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!isValid) return;

    onSubmit({
      name: name.trim(),
      level: levelNum,
      description: description.trim() || undefined,
    });

    setName("");
    setLevel("");
    setDescription("");
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create Role</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="role-name">Name *</Label>
            <Input
              id="role-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Editor, Moderator"
              maxLength={100}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="role-level">Level *</Label>
            <Input
              id="role-level"
              type="number"
              value={level}
              onChange={(e) => setLevel(e.target.value)}
              min={minLevel}
              max={100}
              placeholder={`Min: ${minLevel}`}
            />
            <p className="text-xs text-muted-foreground">
              Lower number = higher authority. Must be greater than {actorRoleLevel}.
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="role-description">Description</Label>
            <Textarea
              id="role-description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe this role's purpose"
              maxLength={500}
              rows={3}
            />
          </div>

          <div className="flex justify-end gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={!isValid || isLoading}>
              {isLoading ? "Creating..." : "Create Role"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
