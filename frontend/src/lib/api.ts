// Small fetch wrapper for the FastAPI backend.

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const TOKEN_KEY = "cleanroom-token";
export const LOGOUT_EVENT = "cleanroom:logout";

export function getToken(): string | null {
  return typeof window === "undefined" ? null : localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (init.body && typeof init.body === "string") headers.set("Content-Type", "application/json");

  const response = await fetch(`${API_URL}${path}`, { ...init, headers });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const detail = typeof body.detail === "string" ? body.detail : response.statusText;
    if (response.status === 401 && token) {
      setToken(null); // expired token: AuthProvider hears this and sends the user to /login
      window.dispatchEvent(new Event(LOGOUT_EVENT));
    }
    throw new ApiError(response.status, detail);
  }
  return response.json() as Promise<T>;
}

export async function login(email: string, password: string): Promise<string> {
  // FastAPI's OAuth2 password flow expects form data with "username" and "password"
  const body = new URLSearchParams({ username: email, password });
  const response = await fetch(`${API_URL}/api/auth/login`, { method: "POST", body });
  if (!response.ok) throw new ApiError(response.status, "Incorrect email or password");
  const data: { access_token: string } = await response.json();
  return data.access_token;
}

export function liveSessionUrl(sessionId: number): string {
  const base = API_URL.replace(/^http/, "ws"); // http -> ws, https -> wss
  return `${base}/ws/sessions/${sessionId}?token=${getToken() ?? ""}`;
}
