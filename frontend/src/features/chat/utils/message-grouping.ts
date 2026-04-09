/**
 * Message grouping utilities.
 *
 * Groups consecutive messages from the same sender within a time window,
 * and inserts date separators between messages from different days.
 */

import type { ChatMessage } from "@/features/chat/types";

/** Max gap (in ms) between messages to be grouped together (5 minutes). */
const GROUP_GAP_MS = 5 * 60 * 1000;

export interface MessageGroup {
  type: "messages";
  senderId: string;
  senderType: string;
  messages: ChatMessage[];
}

export interface DateDivider {
  type: "date";
  date: string;
}

export type MessageListEntry = MessageGroup | DateDivider;

/**
 * Groups messages and inserts date separators.
 * Input messages should be in chronological order (oldest first).
 */
export function groupMessages(messages: ChatMessage[]): MessageListEntry[] {
  if (messages.length === 0) return [];

  const entries: MessageListEntry[] = [];
  let currentDay = "";
  let currentGroup: MessageGroup | null = null;

  for (const msg of messages) {
    const msgDay = toDateKey(msg.created_at);

    // Insert date separator when day changes
    if (msgDay !== currentDay) {
      if (currentGroup) {
        entries.push(currentGroup);
        currentGroup = null;
      }
      entries.push({ type: "date", date: msg.created_at });
      currentDay = msgDay;
    }

    // Check if message belongs to current group
    const belongsToGroup =
      currentGroup &&
      currentGroup.senderId === msg.sender_id &&
      currentGroup.senderType === msg.sender_type &&
      msg.content_type !== "system" &&
      currentGroup.messages[currentGroup.messages.length - 1].content_type !==
        "system" &&
      isWithinGap(
        currentGroup.messages[currentGroup.messages.length - 1].created_at,
        msg.created_at,
      );

    if (belongsToGroup && currentGroup) {
      currentGroup.messages.push(msg);
    } else {
      if (currentGroup) {
        entries.push(currentGroup);
      }
      currentGroup = {
        type: "messages",
        senderId: msg.sender_id,
        senderType: msg.sender_type,
        messages: [msg],
      };
    }
  }

  // Push final group
  if (currentGroup) {
    entries.push(currentGroup);
  }

  return entries;
}

function toDateKey(dateStr: string): string {
  const d = new Date(dateStr);
  return `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`;
}

function isWithinGap(a: string, b: string): boolean {
  return Math.abs(new Date(b).getTime() - new Date(a).getTime()) <= GROUP_GAP_MS;
}
