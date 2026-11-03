import { proxyAlua } from "@/lib/api/proxy";
export const dynamic = "force-dynamic";
export const runtime = "nodejs";
async function proxy(request: Request, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  // Accept the full API path as well as the short path used by the web client.
  const relative = path[0] === "api" && path[1] === "v1" ? path.slice(2) : path;
  return proxyAlua(request, relative);
}
export { proxy as GET, proxy as HEAD, proxy as POST, proxy as PUT, proxy as PATCH, proxy as DELETE, proxy as OPTIONS };
