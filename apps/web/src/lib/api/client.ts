/**
 * Typed fetch wrapper for the FastAPI backend (docs/ARCHITECTURE.md §3.4).
 *
 * The browser only ever talks to same-origin `/api/v1/*`; Next.js rewrites forward it to the API.
 * Errors are normalized from the API's problem+json envelope (docs/API.md §1.1) into `ApiError`.
 */

export const API_PREFIX = "/api/v1";

const CSRF_COOKIE = "atu_csrf";
const CSRF_HEADER = "X-CSRF-Token";
const UNSAFE_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);

export type FieldError = { field: string; code: string; message: string };

type ProblemBody = {
  code?: string;
  title?: string;
  detail?: string | null;
  errors?: FieldError[];
  request_id?: string | null;
};

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly fieldErrors: FieldError[];
  readonly requestId: string | null;

  constructor(init: {
    status: number;
    code: string;
    message: string;
    fieldErrors?: FieldError[];
    requestId?: string | null;
  }) {
    super(init.message);
    this.name = "ApiError";
    this.status = init.status;
    this.code = init.code;
    this.fieldErrors = init.fieldErrors ?? [];
    this.requestId = init.requestId ?? null;
  }

  /** Network failures (status 0), rate limits and server/provider errors may succeed on retry. */
  get isRetryable(): boolean {
    return this.status === 0 || this.status === 429 || this.status >= 500;
  }
}

function readCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.split("; ").find((part) => part.startsWith(`${name}=`));
  return match ? decodeURIComponent(match.slice(name.length + 1)) : null;
}

async function toApiError(response: Response): Promise<ApiError> {
  let body: ProblemBody = {};
  try {
    body = (await response.json()) as ProblemBody;
  } catch {
    // Non-JSON error (e.g. proxy HTML page): fall back to status-only information.
  }
  return new ApiError({
    status: response.status,
    code: body.code ?? "HTTP_ERROR",
    message: body.detail ?? body.title ?? `Request failed with status ${response.status}`,
    fieldErrors: body.errors,
    requestId: body.request_id ?? response.headers.get("x-request-id"),
  });
}

export type ApiRequestInit = Omit<RequestInit, "body"> & { json?: unknown };

export async function apiFetch<T>(path: string, init: ApiRequestInit = {}): Promise<T> {
  const { json, headers: initHeaders, ...rest } = init;
  const method = (rest.method ?? (json === undefined ? "GET" : "POST")).toUpperCase();
  const headers = new Headers(initHeaders);
  headers.set("Accept", "application/json");

  if (json !== undefined) headers.set("Content-Type", "application/json");
  if (UNSAFE_METHODS.has(method)) {
    const csrf = readCookie(CSRF_COOKIE);
    if (csrf) headers.set(CSRF_HEADER, csrf);
  }

  let response: Response;
  try {
    response = await fetch(`${API_PREFIX}${path}`, {
      ...rest,
      method,
      headers,
      credentials: "include",
      body: json === undefined ? undefined : JSON.stringify(json),
    });
  } catch {
    throw new ApiError({
      status: 0,
      code: "NETWORK_ERROR",
      message: "Can't reach the server. Check your connection and try again.",
    });
  }

  if (!response.ok) throw await toApiError(response);
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}
