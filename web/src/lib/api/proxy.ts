/** Fixed Alua upstream only. No cookies, forwarding headers, redirects or shared cache. */
const RESPONSE_LIMIT = 16 * 1024 * 1024;
const REQUEST_LIMIT = 4 * 1024 * 1024;
const PRIVATE_HEADERS = { "Cache-Control": "private, no-store", Vary: "Authorization", "X-Content-Type-Options": "nosniff" };
class SizeLimit extends Error {}
async function read(stream: ReadableStream<Uint8Array> | null, limit: number, signal: AbortSignal) {
  if (!stream) return new Uint8Array();
  const reader = stream.getReader(); const chunks: Uint8Array[] = []; let size = 0;
  const aborted = () => { void reader.cancel().catch(() => {}); };
  signal.addEventListener("abort", aborted, { once: true });
  try {
    signal.throwIfAborted();
    while (true) {
      const { done, value } = await reader.read(); signal.throwIfAborted();
      if (done) break;
      size += value.byteLength; if (size > limit) throw new SizeLimit(); chunks.push(value);
    }
    const result = new Uint8Array(size); let offset = 0;
    for (const chunk of chunks) { result.set(chunk, offset); offset += chunk.byteLength; }
    return result;
  } finally { signal.removeEventListener("abort", aborted); void reader.cancel().catch(() => {}); }
}
function failure(status: number, code: string) {
  return Response.json({ error: { code, message: "The Alua API request could not complete." } }, { status, headers: PRIVATE_HEADERS });
}
export async function proxyAlua(request: Request, segments: string[], configured = process.env.NEXT_PUBLIC_API_BASE_URL, timeout = 12_000): Promise<Response> {
  if (!configured) return failure(503, "api_not_configured");
  let base: URL;
  try {
    base = new URL(configured);
    if (base.username || base.password || base.search || base.hash ||
      !(base.protocol === "https:" || base.protocol === "http:" && ["localhost", "127.0.0.1", "[::1]"].includes(base.hostname))) throw Error();
  } catch { return failure(503, "api_not_configured"); }
  if (!segments.length || segments.some(p => !/^[a-zA-Z0-9._~-]+$/.test(p) || p === "." || p === "..")) return failure(400, "invalid_api_path");
  const target = new URL(`${base.href.replace(/\/$/, "")}/${segments.map(encodeURIComponent).join("/")}`);
  target.search = new URL(request.url).search;
  const controller = new AbortController();
  const abort = () => controller.abort(); request.signal.addEventListener("abort", abort, { once: true });
  const timer = setTimeout(abort, timeout);
  try {
    if (request.signal.aborted) controller.abort();
    const headers = new Headers();
    for (const name of ["authorization", "accept", "content-type", "if-none-match", "if-modified-since"]) {
      const value = request.headers.get(name); if (value) headers.set(name, value);
    }
    let body: ArrayBuffer | undefined;
    if (!["GET", "HEAD"].includes(request.method)) {
      try { body = (await read(request.body, REQUEST_LIMIT, controller.signal)).buffer; }
      catch (error) { if (error instanceof SizeLimit) return failure(413, "request_too_large"); throw error; }
    }
    const upstream = await fetch(target, { method: request.method, headers, body, redirect: "manual", cache: "no-store", signal: controller.signal });
    if (upstream.status >= 300 && upstream.status < 400 && upstream.status !== 304) {
      await upstream.body?.cancel(); return failure(502, "upstream_redirect_rejected");
    }
    const responseHeaders = new Headers(PRIVATE_HEADERS);
    for (const name of ["content-type", "etag", "last-modified", "retry-after", "x-image-width", "x-image-height"]) {
      const value = upstream.headers.get(name); if (value) responseHeaders.set(name, value);
    }
    // Buffer bounded bodies so a stalled response becomes 504 before sending headers.
    const bytes = await read(upstream.body, RESPONSE_LIMIT, controller.signal);
    return new Response(request.method === "HEAD" || [204, 205, 304].includes(upstream.status) ? null : bytes, { status: upstream.status, headers: responseHeaders });
  } catch (error) {
    if (controller.signal.aborted) return failure(504, "timeout");
    if (error instanceof SizeLimit) return failure(502, "upstream_response_too_large");
    return failure(502, "upstream_unavailable");
  } finally { clearTimeout(timer); request.signal.removeEventListener("abort", abort); }
}
