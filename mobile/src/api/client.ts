/**
 * Client HTTP, bascule données fictives / API.
 *
 * EXPO_PUBLIC_USE_MOCKS=true (défaut) : les appels sont servis par src/mocks/server.ts.
 * EXPO_PUBLIC_USE_MOCKS=false : appels HTTP vers EXPO_PUBLIC_API_URL (routes de docs/01_ARCHITECTURE.md).
 * Sur un téléphone, `localhost` désigne le téléphone : utiliser l'adresse IP locale de l'ordinateur,
 * ou l'URL API Gateway une fois P4 déployée.
 */
import { MockInvalid, MockNotFound } from "../mocks/server";

export const USE_MOCKS = process.env.EXPO_PUBLIC_USE_MOCKS !== "false";
export const API_URL = (process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

export const isNotFound = (e: unknown) => e instanceof ApiError && e.status === 404;

async function request<T>(method: "GET" | "POST", path: string, body?: unknown): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      method,
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError(0, `API injoignable (${API_URL}). Vérifiez EXPO_PUBLIC_API_URL.`);
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const j = await res.json();
      if (typeof j?.detail === "string") detail = j.detail;
    } catch {
      // corps vide ou non JSON
    }
    throw new ApiError(res.status, detail || `Erreur ${res.status}`);
  }
  return (await res.json()) as T;
}

export const http = {
  get: <T>(path: string) => request<T>("GET", path),
  post: <T>(path: string, body: unknown) => request<T>("POST", path, body),
};

/** Exécute la version fictive en traduisant ses erreurs comme le ferait l'API. */
export async function mocked<T>(fn: () => Promise<T>): Promise<T> {
  try {
    return await fn();
  } catch (e) {
    if (e instanceof MockNotFound) throw new ApiError(404, e.message);
    if (e instanceof MockInvalid) throw new ApiError(422, e.message);
    throw e;
  }
}
