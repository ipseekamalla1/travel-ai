import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, apiFetch } from "./client";
import { shouldRetry } from "./query-client";

const fetchMock = vi.fn<typeof fetch>();

function jsonResponse(status: number, body: unknown, headers: Record<string, string> = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", ...headers },
  });
}

beforeEach(() => {
  vi.stubGlobal("fetch", fetchMock);
  document.cookie = "atu_csrf=token-123";
});

afterEach(() => {
  vi.unstubAllGlobals();
  fetchMock.mockReset();
  document.cookie = "atu_csrf=; expires=Thu, 01 Jan 1970 00:00:00 GMT";
});

describe("apiFetch", () => {
  it("calls the same-origin versioned API and returns JSON", async () => {
    fetchMock.mockResolvedValue(jsonResponse(200, { status: "ok" }));

    await expect(apiFetch("/health")).resolves.toEqual({ status: "ok" });

    const [url, init] = fetchMock.mock.calls[0]!;
    expect(url).toBe("/api/v1/health");
    expect(init?.method).toBe("GET");
    expect(init?.credentials).toBe("include");
  });

  it("sends JSON bodies and the CSRF token on unsafe methods", async () => {
    document.cookie = "atu_csrf=token-123";
    fetchMock.mockResolvedValue(jsonResponse(201, { id: "t1" }));

    await apiFetch("/trips", { json: { name: "Japan" } });

    const init = fetchMock.mock.calls[0]![1]!;
    const headers = new Headers(init.headers);
    expect(init.method).toBe("POST");
    expect(init.body).toBe(JSON.stringify({ name: "Japan" }));
    expect(headers.get("Content-Type")).toBe("application/json");
    expect(headers.get("X-CSRF-Token")).toBe("token-123");
  });

  it("bootstraps a CSRF token before the first unsafe request", async () => {
    document.cookie = "atu_csrf=; expires=Thu, 01 Jan 1970 00:00:00 GMT";
    fetchMock
      .mockResolvedValueOnce(jsonResponse(200, { csrf_token: "fresh-token" }))
      .mockResolvedValueOnce(jsonResponse(201, { id: "t1" }));

    await apiFetch("/trips", { json: { name: "Japan" } });

    expect(fetchMock.mock.calls[0]![0]).toBe("/api/v1/auth/csrf");
    expect(new Headers(fetchMock.mock.calls[1]![1]!.headers).get("X-CSRF-Token")).toBe(
      "fresh-token",
    );
  });

  it("refreshes a stale CSRF token once and retries", async () => {
    fetchMock
      .mockResolvedValueOnce(jsonResponse(403, { code: "CSRF_FAILED", errors: [] }))
      .mockResolvedValueOnce(jsonResponse(200, { csrf_token: "rotated" }))
      .mockResolvedValueOnce(jsonResponse(200, { ok: true }));

    await expect(apiFetch("/auth/logout", { method: "POST" })).resolves.toEqual({ ok: true });

    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(new Headers(fetchMock.mock.calls[2]![1]!.headers).get("X-CSRF-Token")).toBe("rotated");
  });

  it("does not retry other 403 errors", async () => {
    fetchMock.mockResolvedValue(jsonResponse(403, { code: "FORBIDDEN", errors: [] }));

    const error = (await apiFetch("/trips", { json: {} }).catch((e: unknown) => e)) as ApiError;

    expect(error.code).toBe("FORBIDDEN");
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("does not send the CSRF token on safe methods", async () => {
    document.cookie = "atu_csrf=token-123";
    fetchMock.mockResolvedValue(jsonResponse(200, {}));

    await apiFetch("/trips");

    expect(new Headers(fetchMock.mock.calls[0]![1]!.headers).has("X-CSRF-Token")).toBe(false);
  });

  it("returns undefined for 204 No Content", async () => {
    fetchMock.mockResolvedValue(new Response(null, { status: 204 }));

    await expect(apiFetch("/trips/1", { method: "DELETE" })).resolves.toBeUndefined();
  });

  it("maps the problem+json envelope to ApiError with field errors", async () => {
    fetchMock.mockResolvedValue(
      jsonResponse(422, {
        code: "VALIDATION_ERROR",
        title: "Validation failed",
        detail: "One or more fields are invalid.",
        errors: [{ field: "end_date", code: "DATE_BEFORE_START", message: "Too early." }],
        request_id: "req-1",
      }),
    );

    const error = await apiFetch("/trips", { json: {} }).catch((e: unknown) => e);

    expect(error).toBeInstanceOf(ApiError);
    const apiError = error as ApiError;
    expect(apiError.status).toBe(422);
    expect(apiError.code).toBe("VALIDATION_ERROR");
    expect(apiError.fieldErrors).toEqual([
      { field: "end_date", code: "DATE_BEFORE_START", message: "Too early." },
    ]);
    expect(apiError.requestId).toBe("req-1");
    expect(apiError.isRetryable).toBe(false);
  });

  it("handles non-JSON error bodies", async () => {
    fetchMock.mockResolvedValue(
      new Response("<html>Bad gateway</html>", {
        status: 502,
        headers: { "x-request-id": "req-2" },
      }),
    );

    const error = (await apiFetch("/health").catch((e: unknown) => e)) as ApiError;

    expect(error.status).toBe(502);
    expect(error.code).toBe("HTTP_ERROR");
    expect(error.requestId).toBe("req-2");
    expect(error.isRetryable).toBe(true);
  });

  it("turns network failures into a retryable NETWORK_ERROR", async () => {
    fetchMock.mockRejectedValue(new TypeError("Failed to fetch"));

    const error = (await apiFetch("/health").catch((e: unknown) => e)) as ApiError;

    expect(error.status).toBe(0);
    expect(error.code).toBe("NETWORK_ERROR");
    expect(error.isRetryable).toBe(true);
  });
});

describe("shouldRetry", () => {
  const serverError = new ApiError({ status: 503, code: "PROVIDER_UNAVAILABLE", message: "" });
  const clientError = new ApiError({ status: 404, code: "NOT_FOUND", message: "" });

  it("retries retryable errors up to the limit", () => {
    expect(shouldRetry(0, serverError)).toBe(true);
    expect(shouldRetry(2, serverError)).toBe(false);
  });

  it("never retries client errors", () => {
    expect(shouldRetry(0, clientError)).toBe(false);
  });
});
