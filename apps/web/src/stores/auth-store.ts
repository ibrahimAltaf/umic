"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { TokenResponse, User } from "@/types/auth";
import { apiRequest } from "@/lib/api";

type AuthState = {
  accessToken: string | null;
  refreshToken: string | null;
  user: User | null;
  isHydrated: boolean;
  setHydrated: (value: boolean) => void;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  fetchMe: () => Promise<void>;
  clear: () => void;
};

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      accessToken: null,
      refreshToken: null,
      user: null,
      isHydrated: false,
      setHydrated: (value) => set({ isHydrated: value }),
      clear: () =>
        set({ accessToken: null, refreshToken: null, user: null }),
      login: async (email, password) => {
        const tokens = await apiRequest<TokenResponse>("/api/v1/auth/login", {
          method: "POST",
          body: { email, password },
        });
        set({
          accessToken: tokens.access_token,
          refreshToken: tokens.refresh_token,
        });
        const user = await apiRequest<User>("/api/v1/auth/me", {
          token: tokens.access_token,
        });
        set({ user });
      },
      logout: async () => {
        const { accessToken, refreshToken } = get();
        if (accessToken && refreshToken) {
          try {
            await apiRequest("/api/v1/auth/logout", {
              method: "POST",
              token: accessToken,
              body: { refresh_token: refreshToken },
            });
          } catch {
            // ignore logout network errors
          }
        }
        get().clear();
      },
      fetchMe: async () => {
        const token = get().accessToken;
        if (!token) {
          set({ user: null });
          return;
        }
        const user = await apiRequest<User>("/api/v1/auth/me", { token });
        set({ user });
      },
    }),
    {
      name: "umic-auth",
      partialize: (state) => ({
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
      }),
      onRehydrateStorage: () => (state) => {
        state?.setHydrated(true);
      },
    },
  ),
);
