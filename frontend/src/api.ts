function getApiBase(): string {
  const explicit = import.meta.env.VITE_API_BASE as string | undefined;
  if (explicit !== undefined && explicit !== "") {
    return explicit;
  }
  // Режим Vite dev: см. proxy в vite.config.ts — относительный путь к своему origin.
  if (import.meta.env.DEV) {
    return "/api/v1";
  }
  return "http://localhost:8000/api/v1";
}

const BASE = getApiBase();

export function getToken(): string | null {
  return localStorage.getItem("token");
}

export function setToken(token: string | null): void {
  if (token) {
    localStorage.setItem("token", token);
  } else {
    localStorage.removeItem("token");
  }
}

export async function apiFetch(
  path: string,
  init?: RequestInit,
): Promise<Response> {
  const token = getToken();
  const headers = new Headers(init?.headers);
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  const body = init?.body;
  if (
    !headers.has("Content-Type") &&
    body &&
    !(body instanceof FormData) &&
    !(body instanceof URLSearchParams)
  ) {
    headers.set("Content-Type", "application/json");
  }
  return fetch(`${BASE}${path}`, { ...init, headers });
}

export async function apiJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await apiFetch(path, init);
  if (!res.ok) {
    const text = await res.text();
    let detail = text;
    try {
      const j = JSON.parse(text) as { detail?: string | unknown };
      if (typeof j.detail === "string") {
        detail = j.detail;
      } else if (Array.isArray(j.detail)) {
        detail = JSON.stringify(j.detail);
      }
    } catch {
      /* ignore */
    }
    throw new Error(detail || res.statusText);
  }
  if (res.status === 204) {
    return undefined as T;
  }
  return res.json() as Promise<T>;
}

export { BASE };
