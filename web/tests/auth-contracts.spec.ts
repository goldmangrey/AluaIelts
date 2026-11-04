import { test, expect } from "@playwright/test";
import { ApiError, createApiClient } from "../src/lib/api/client";
import { resolveLearner } from "../src/features/auth/api";
import { safeReturnPath } from "../src/features/auth/redirect";
import { withTimeout } from "../src/lib/timeout";
import { authMessage } from "../src/features/auth/messages";

test("only identity_not_allowed provisions, retries preserve the same identity", async () => {
  const calls: unknown[] = [];
  const request: ReturnType<typeof createApiClient> = async (path, _signal, options) => {
    calls.push([path, options]);
    if (path === "/me") throw new ApiError(403, "identity_not_allowed");
    return { uid: "learner-id", display_name: "Alua Learner", email: null };
  };
  await expect(resolveLearner(request, " Alua Learner ")).resolves.toMatchObject({ uid: "learner-id" });
  expect(calls).toEqual([["/me", undefined], ["/auth/register", { method: "POST", body: { display_name: "Alua Learner" } }]]);
  for (const failure of [new ApiError(403, "forbidden"), new ApiError(401, "unauthorized"), new ApiError(503, "unavailable")]) {
    let count = 0;
    await expect(resolveLearner(async () => { count++; throw failure; })).rejects.toBe(failure);
    expect(count).toBe(1);
  }
});

test("redirects cannot escape origin or loop into auth routes", () => {
  expect(safeReturnPath("/reading/cambridge-12?test=5")).toBe("/reading/cambridge-12?test=5");
  for (const path of ["https://evil.test", "//evil.test", "/\\evil.test", "/login?next=/login", "/register", "/\n/evil.test"]) {
    expect(safeReturnPath(path)).toBe("/");
  }
});

test("SDK and token acquisition deadlines settle instead of infinite loading", async () => {
  await expect(withTimeout(new Promise(() => {}), 20)).rejects.toMatchObject({ code: "timeout" });
  const oldBase = process.env.NEXT_PUBLIC_API_BASE_URL;
  process.env.NEXT_PUBLIC_API_BASE_URL = "http://localhost:8000/api/v1";
  try {
    await expect(createApiClient(() => new Promise(() => {}), 20)("/reading/books")).rejects.toMatchObject({ code: "timeout" });
  } finally {
    if (oldBase === undefined) delete process.env.NEXT_PUBLIC_API_BASE_URL;
    else process.env.NEXT_PUBLIC_API_BASE_URL = oldBase;
  }
});

test("reset/login errors do not reveal account existence", () => {
  expect(authMessage({ code: "auth/user-not-found" })).toBe(authMessage({ code: "auth/wrong-password" }));
  expect(authMessage({ code: "auth/invalid-credential" })).toBe(authMessage({ code: "auth/wrong-password" }));
});

test("real HTTP 5xx and a stalled response body settle with bounded errors", async () => {
  const { createServer } = await import("node:http");
  let stall = false;
  let requests = 0;
  const server = createServer((_request, response) => {
    requests++;
    response.writeHead(stall ? 200 : 503, { "Content-Type": "application/json" });
    if (stall) { response.write("{"); return; }
    response.end(JSON.stringify({ error: { code: "service_unavailable" } }));
  });
  await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
  const address = server.address();
  if (!address || typeof address === "string") throw new Error("Local fault fixture unavailable");
  const oldBase = process.env.NEXT_PUBLIC_API_BASE_URL;
  process.env.NEXT_PUBLIC_API_BASE_URL = `http://127.0.0.1:${address.port}/api/v1`;
  try {
    await expect(createApiClient(async () => "local-fixture-token")("/reading/books")).rejects.toMatchObject({ status: 503, code: "service_unavailable" });
    expect(requests).toBe(1);
    stall = true;
    await expect(createApiClient(async () => "local-fixture-token", 100)("/reading/books")).rejects.toMatchObject({ code: "timeout" });
  } finally {
    server.closeAllConnections();
    await new Promise<void>((resolve) => server.close(() => resolve()));
    if (oldBase === undefined) delete process.env.NEXT_PUBLIC_API_BASE_URL;
    else process.env.NEXT_PUBLIC_API_BASE_URL = oldBase;
  }
});


test("restored Google errors preserve the existing account and never suggest merging", () => {
  expect(authMessage({code:"auth/account-exists-with-different-credential"})).toContain("existing method");
  expect(authMessage({code:"auth/credential-already-in-use"})).toContain("have not been merged");
  expect(authMessage({code:"auth/popup-closed-by-user"})).toContain("cancelled");
});
