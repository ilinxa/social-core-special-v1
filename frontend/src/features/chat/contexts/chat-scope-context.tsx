"use client";

/**
 * Chat Scope Context
 * ==================
 * Provides scope isolation for chat components.
 *
 * Components below this context never need to know which scope they're in.
 * Scope determines: API params (scope_type, scope_id), entity inbox visibility,
 * and participant type for entity messaging.
 */

import { createContext, useContext, type ReactNode } from "react";

import type { ParticipantType, ScopeType } from "@/features/chat/types";

// =============================================================================
// CONTEXT VALUE
// =============================================================================

export interface ChatScopeValue {
  /** The scope type for filtering conversations */
  scopeType: ScopeType;
  /** The scope ID (business or platform UUID). Null for global. */
  scopeId: string | null;
  /** Participant type when chatting as an entity (business/platform). */
  participantType?: ParticipantType;
  /** Participant ID when chatting as an entity. */
  participantId?: string;
  /** Business slug for URL construction (business scope only). */
  slug?: string;
}

const ChatScopeContext = createContext<ChatScopeValue | null>(null);

// =============================================================================
// PROVIDER
// =============================================================================

interface ChatScopeProviderProps {
  value: ChatScopeValue;
  children: ReactNode;
}

export function ChatScopeProvider({ value, children }: ChatScopeProviderProps) {
  return (
    <ChatScopeContext.Provider value={value}>
      {children}
    </ChatScopeContext.Provider>
  );
}

// =============================================================================
// HOOK
// =============================================================================

export function useChatScope(): ChatScopeValue {
  const context = useContext(ChatScopeContext);
  if (!context) {
    throw new Error("useChatScope must be used within a ChatScopeProvider");
  }
  return context;
}
