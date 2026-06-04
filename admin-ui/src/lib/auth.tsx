"use client";
/**
 * Auth context — single fetch of `/api/auth/me`, exposed via `useAuth()`.
 *
 * The browser session is established by the httpOnly cookie set by
 * `/api/auth/login` (ADR-0017). Most components don't care about the user
 * id; the realtime layer however needs `tenant_id` to build topic strings
 * (`tenant:{tid}:model:{model}:list`), so we fetch the profile once at
 * mount and cache it in context for the rest of the tree.
 */
import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api } from "./api";

export interface AuthUser {
  id: string;
  email: string;
  name: string;
  tenant_id: string | null;
  is_superadmin: boolean;
  is_active: boolean;
  language: string;
  timezone: string;
  totp_enabled: boolean;
  last_login: string | null;
}

export interface AuthState {
  user: AuthUser | null;
  hydrated: boolean;
  refreshUser: () => Promise<void>;
}

const DEFAULT: AuthState = { user: null, hydrated: false, refreshUser: async () => {} };
const AuthContext = createContext<AuthState>(DEFAULT);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<Omit<AuthState, "refreshUser">>({ user: null, hydrated: false });

  const refreshUser = useCallback(async () => {
    try {
      const { data } = await api.get<AuthUser>("/auth/me", { skipGlobalErrorToast: true });
      setState({ user: data, hydrated: true });
    } catch {
      setState({ user: null, hydrated: true });
    }
  }, []);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const path = window.location.pathname;
      if (path === "/login" || path === "/welcome") {
        setState({ user: null, hydrated: true });
        return;
      }
    }
    void refreshUser();
  }, [refreshUser]);

  useEffect(() => {
    const onUpdated = () => { void refreshUser(); };
    window.addEventListener("orbiteus:user-preferences-updated", onUpdated);
    return () => window.removeEventListener("orbiteus:user-preferences-updated", onUpdated);
  }, [refreshUser]);

  return (
    <AuthContext.Provider value={{ ...state, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  return useContext(AuthContext);
}
