export interface ValidationDetail {loc:(string|number)[];type:string}
export class ApiError extends Error {
  constructor(public readonly status: number, public readonly code: string, public readonly detail?:ValidationDetail[]) {
    super(code);
    this.name = "ApiError";
  }
}
export type TokenProvider = (forceRefresh?: boolean) => Promise<string | null>;

/** Direct FastAPI client. Private payloads never enter a shared Next.js cache. */
export function createApiClient(getToken: TokenProvider, timeoutMilliseconds = 15_000) {
  return async function request(path: `/${string}`, signal?: AbortSignal, options?: { method: "POST" | "PUT" | "PATCH"; body: unknown }, responseType: "json" | "blob" = "json"): Promise<unknown> {
    const configured = process.env.NEXT_PUBLIC_API_BASE_URL;
    if (!configured) throw new ApiError(0, "api_not_configured");
    let base: URL;
    try { base = new URL(configured); } catch { throw new ApiError(0, "api_not_configured"); }
    if (!(["http:", "https:"].includes(base.protocol)) || base.username || base.password || base.search || base.hash ||
        (base.protocol !== "https:" && !["localhost", "127.0.0.1", "[::1]"].includes(base.hostname))) {
      throw new ApiError(0, "api_not_configured");
    }
    // Browser calls remain same-origin; Next forwards to the fixed existing API.
    const endpoint = typeof window === "undefined" ? base.href.replace(/\/$/, "") : "/api/alua";
    const controller = new AbortController();
    const abort = () => controller.abort();
    signal?.addEventListener("abort", abort, { once: true });
    if (signal?.aborted) controller.abort();
    const timer = setTimeout(abort, timeoutMilliseconds);
    try {
      // Bounded retry only for a stale ID token; no automatic retry of mutations.
      for (let attempt = 0; attempt < 2; attempt++) {
        controller.signal.throwIfAborted();
        let tokenAbort: (() => void) | undefined;
        const token = await Promise.race([
          getToken(attempt === 1),
          new Promise<never>((_, reject) => {
            tokenAbort = () => reject(new DOMException("Aborted", "AbortError"));
            controller.signal.addEventListener("abort", tokenAbort, { once: true });
          }),
        ]).finally(() => {
          if (tokenAbort) controller.signal.removeEventListener("abort", tokenAbort);
        });
        controller.signal.throwIfAborted();
        if (!token) throw new ApiError(401, "sign_in_required");
        const response = await fetch(`${endpoint}${path}`, {
          method: options?.method ?? "GET",
          body: options ? JSON.stringify(options.body) : undefined,
          headers: { Accept: "application/json", Authorization: `Bearer ${token}`, ...(options ? { "Content-Type": "application/json" } : {}) },
          cache: "no-store", credentials: "omit", redirect: "error", signal: controller.signal,
        });
        if (response.status === 401 && attempt === 0 && !options) continue;
        if (!response.ok) {
          let code = "request_failed";
          let detail:ValidationDetail[]|undefined;
          try {
            const body: unknown = await response.json();
            if (body && typeof body === "object" && "error" in body && body.error &&
                typeof body.error === "object" && "code" in body.error && typeof body.error.code === "string") {
              code = body.error.code;
            }
            if(response.status===422&&body&&typeof body==="object"&&"detail" in body&&Array.isArray(body.detail)){
              // Never retain Pydantic's input/ctx: these may contain answer text.
              detail=body.detail.filter((d):d is {loc:(string|number)[];type:string}=>!!d&&typeof d==="object"&&Array.isArray(d.loc)&&d.loc.every((v:unknown)=>typeof v==="string"||typeof v==="number")&&typeof d.type==="string").map(d=>({loc:d.loc,type:d.type}));
              if(detail.length)code="request_validation_error";
            }
          } catch { /* Error bodies may be non-JSON at an upstream gateway. */ }
          throw new ApiError(response.status, code, detail);
        }
        try { return responseType === "blob" ? await response.blob() : await response.json(); }
        catch {
          if (controller.signal.aborted) controller.signal.throwIfAborted();
          throw new ApiError(502, "unexpected_response");
        }
      }
      throw new ApiError(401, "session_expired");
    } catch (error) {
      if (error instanceof ApiError) throw error;
      if (signal?.aborted) throw error;
      if (controller.signal.aborted) throw new ApiError(0, "timeout");
      throw new ApiError(0, "network_error");
    } finally {
      clearTimeout(timer);
      signal?.removeEventListener("abort", abort);
    }
  };
}
