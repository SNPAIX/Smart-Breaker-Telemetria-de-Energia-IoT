import { createContext, useContext, useMemo, useState, type ReactNode } from "react";

import { apiClient, clearStoredToken, getStoredToken, storeToken } from "../api/client";
import { decodeJwt, isTokenExpired } from "./jwt";

interface AuthUser {
  id: number;
  role: string;
}

interface AuthContextValue {
  user: AuthUser | null;
  isAuthenticated: boolean;
  isAdmin: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function userFromToken(token: string | null): AuthUser | null {
  if (!token) return null;
  const decoded = decodeJwt(token);
  if (!decoded || isTokenExpired(decoded)) return null;
  return { id: Number(decoded.sub), role: decoded.role };
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(() => userFromToken(getStoredToken()));

  const login = async (email: string, password: string) => {
    const body = new URLSearchParams();
    body.set("username", email);
    body.set("password", password);

    const response = await apiClient.post("/api/v1/auth/login", body, {
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    });

    const token = response.data.access_token as string;
    storeToken(token);
    setUser(userFromToken(token));
  };

  const logout = () => {
    clearStoredToken();
    setUser(null);
  };

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      isAuthenticated: user !== null,
      isAdmin: user?.role === "admin",
      login,
      logout,
    }),
    [user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth debe usarse dentro de AuthProvider");
  }
  return context;
}
