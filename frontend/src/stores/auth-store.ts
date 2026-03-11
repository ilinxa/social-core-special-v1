"use client";

import { create } from "zustand";
import { devtools } from "zustand/middleware";

import type { User } from "@/types";

// =============================================================================
// STATE & ACTIONS
// =============================================================================

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isInitialized: boolean;
}

interface AuthActions {
  setUser: (user: User) => void;
  clearUser: () => void;
  setInitialized: () => void;
}

type AuthStore = AuthState & AuthActions;

const initialState: AuthState = {
  user: null,
  isAuthenticated: false,
  isInitialized: false,
};

// =============================================================================
// STORE
// =============================================================================

export const useAuthStore = create<AuthStore>()(
  devtools(
    (set) => ({
      ...initialState,

      setUser: (user: User) => set({ user, isAuthenticated: true }, false, "auth/setUser"),

      clearUser: () => set({ user: null, isAuthenticated: false }, false, "auth/clearUser"),

      setInitialized: () => set({ isInitialized: true }, false, "auth/setInitialized"),
    }),
    { name: "auth-store" },
  ),
);

// =============================================================================
// SELECTOR HOOKS (export these, not the raw store)
// =============================================================================

export function useUser(): User | null {
  return useAuthStore((s) => s.user);
}

export function useIsAuthenticated(): boolean {
  return useAuthStore((s) => s.isAuthenticated);
}

export function useIsInitialized(): boolean {
  return useAuthStore((s) => s.isInitialized);
}

// =============================================================================
// NON-REACT ACCESS (for API layer / outside components)
// =============================================================================

export function getAuthStore() {
  return useAuthStore.getState();
}
