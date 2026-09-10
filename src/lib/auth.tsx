import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { getBackendUrl } from "./api";

export interface AppUser {
  id: string;
  name: string;
  email: string;
  role: string;
  createdAt: string;
}

const TOKEN_KEY = "qpgen_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}
function setToken(t: string | null) {
  if (typeof window === "undefined") return;
  if (t) localStorage.setItem(TOKEN_KEY, t);
  else localStorage.removeItem(TOKEN_KEY);
}

function base() {
  const url = getBackendUrl();
  if (!url) throw new Error("Accounts need the Python backend running. Set VITE_BACKEND_URL.");
  return url.replace(/\/$/, "");
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${base()}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error((data as any)?.detail ?? `Request failed (${res.status})`);
  return data as T;
}

interface AuthValue {
  user: AppUser | null;
  loading: boolean;
  backendConfigured: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (name: string, email: string, password: string) => Promise<void>;
  signOut: () => void;
}

const AuthContext = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AppUser | null>(null);
  const [loading, setLoading] = useState(true);
  const backendConfigured = typeof window !== "undefined" && !!getBackendUrl();

  useEffect(() => {
    const token = getToken();
    if (!token || !backendConfigured) {
      setLoading(false);
      return;
    }
    fetch(`${base()}/auth/me`, { headers: { Authorization: `Bearer ${token}` } })
      .then(async (r) => (r.ok ? ((await r.json()) as AppUser) : null))
      .then((u) => {
        if (!u) setToken(null);
        setUser(u);
      })
      .catch(() => setToken(null))
      .finally(() => setLoading(false));
  }, [backendConfigured]);

  const signIn = useCallback(async (email: string, password: string) => {
    const out = await post<{ token: string; user: AppUser }>("/auth/login", { email, password });
    setToken(out.token);
    setUser(out.user);
  }, []);

  const signUp = useCallback(async (name: string, email: string, password: string) => {
    const out = await post<{ token: string; user: AppUser }>("/auth/register", { name, email, password });
    setToken(out.token);
    setUser(out.user);
  }, []);

  const signOut = useCallback(() => {
    setToken(null);
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({ user, loading, backendConfigured, signIn, signUp, signOut }),
    [user, loading, backendConfigured, signIn, signUp, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
