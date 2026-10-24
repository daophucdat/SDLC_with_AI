import type { Problem } from "./types";

export const CSRF_HEADER = "X-CSRF-Token";
const CSRF_COOKIES = ["__Host-csrf", "csrf"]; // plain name in http dev setups (COOKIE_SECURE=false)
const UNSAFE = new Set(["POST", "PUT", "PATCH", "DELETE"]);

export class ApiError extends Error {
  constructor(public readonly problem: Problem) {
    super(problem.code);
  }
  get code(): string {
    return this.problem.code;
  }
  get status(): number {
    return this.problem.status;
  }
}

export function readCookie(name: string): string | null {
  for (const part of document.cookie.split(";")) {
    const [k, ...v] = part.trim().split("=");
    if (k === name) return decodeURIComponent(v.join("="));
  }
  return null;
}

export function csrfToken(): string | null {
  for (const n of CSRF_COOKIES) {
    const v = readCookie(n);
    if (v) return v;
  }
  return null;
}

export function loginUrl(returnTo: string = window.location.pathname + window.location.search): string {
  return `/auth/login?returnTo=${encodeURIComponent(returnTo)}`;
}

/** Navigation is a seam so tests can observe redirects without a real page load. */
export const nav = { assign: (url: string) => window.location.assign(url) };

// US-103: by default a 401 sends the browser to the IdP. Inside the workspace a handler replaces this, so the
// user sees "Phiên đã hết hạn" and keeps the question being typed (EC-17) instead of losing the page.
const redirectToLogin = () => nav.assign(loginUrl());
let authRequiredHandler: () => void = redirectToLogin;

export function setAuthRequiredHandler(handler: (() => void) | null): void {
  authRequiredHandler = handler ?? redirectToLogin;
}

export function authRequired(): void {
  authRequiredHandler();
}

export function problemOf(status: number, body: unknown): Problem {
  if (body && typeof (body as Problem).code === "string") return { ...(body as Problem), status };
  return { status, code: status >= 500 ? "INTERNAL" : "UNKNOWN" };
}

/** fetch wrapper: same-origin cookies, CSRF header on unsafe methods, problem+json → ApiError, 401 → login. */
export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const method = (init.method ?? "GET").toUpperCase();
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  if (UNSAFE.has(method)) {
    const token = csrfToken();
    if (token) headers.set(CSRF_HEADER, token);
  }
  const res = await fetch(path, { ...init, method, headers, credentials: "same-origin" });
  if (!res.ok) {
    const problem = problemOf(res.status, await res.json().catch(() => null));
    if (problem.code === "AUTH_REQUIRED") authRequired();
    throw new ApiError(problem);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}
