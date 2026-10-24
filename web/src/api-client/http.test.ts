import { fakeResponse, mockFetch } from "../test/utils";
import { api, ApiError, CSRF_HEADER, nav } from "./http";

afterEach(() => {
  vi.unstubAllGlobals();
  document.cookie = "__Host-csrf=; expires=Thu, 01 Jan 1970 00:00:00 GMT";
  document.cookie = "csrf=; expires=Thu, 01 Jan 1970 00:00:00 GMT";
});

describe("api()", () => {
  it("sends the CSRF cookie value as a header on unsafe methods only", async () => {
    document.cookie = "csrf=tok-123";
    const calls = mockFetch(() => ({ status: 200, body: {} }));
    await api("/api/v1/x", { method: "POST" });
    await api("/api/v1/x");
    expect(new Headers(calls[0].init.headers).get(CSRF_HEADER)).toBe("tok-123");
    expect(new Headers(calls[1].init.headers).get(CSRF_HEADER)).toBeNull();
    expect(calls[0].init.credentials).toBe("same-origin");
  });

  it("turns problem+json into ApiError with code and extras", async () => {
    mockFetch(() => ({ status: 409, body: { code: "DUPLICATE_DOCUMENT", existingId: "d-9", traceId: "t" } }));
    const err = (await api("/api/v1/documents").catch((e) => e)) as ApiError;
    expect(err).toBeInstanceOf(ApiError);
    expect(err.code).toBe("DUPLICATE_DOCUMENT");
    expect(err.status).toBe(409);
    expect(err.problem.existingId).toBe("d-9");
  });

  it("maps a non-JSON 502 to INTERNAL", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => fakeResponse(502, "bad gateway")),
    );
    const err = (await api("/api/v1/me").catch((e) => e)) as ApiError;
    expect(err.code).toBe("INTERNAL");
  });

  it("redirects to /auth/login with returnTo on AUTH_REQUIRED", async () => {
    const assign = vi.spyOn(nav, "assign").mockImplementation(() => undefined);
    window.history.pushState({}, "", "/library?x=1");
    mockFetch(() => ({ status: 401, body: { code: "AUTH_REQUIRED" } }));
    await expect(api("/api/v1/me")).rejects.toBeInstanceOf(ApiError);
    expect(assign).toHaveBeenCalledWith("/auth/login?returnTo=%2Flibrary%3Fx%3D1");
    assign.mockRestore();
  });
});
