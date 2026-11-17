import { test, expect } from "@playwright/test";
import { ApiError, createApiClient } from "../src/lib/api/client";
import { resolveLearner } from "../src/features/auth/api";
import { safeReturnPath } from "../src/features/auth/redirect";
import { withTimeout } from "../src/lib/timeout";
import { authMessage } from "../src/features/auth/messages";
import { elements, formHarness, sessionHarness } from "./helpers/auth-harness";
import type { Session } from "../src/features/auth/session";
import { ME_CLIENT_TIMEOUT_MS, ME_PROXY_TIMEOUT_MS, ME_RECOVERY_TIMEOUT_MS } from "../src/lib/api/deadlines";

test("only identity_not_allowed provisions, retries preserve the same identity", async () => {
  const calls: unknown[] = [];
  const request: ReturnType<typeof createApiClient> = async (path, _signal, options) => {
    calls.push([path, options]);
    if (path === "/me") throw new ApiError(403, "identity_not_allowed");
    return { uid: "learner-id", display_name: "Alua Learner", email: null };
  };
  await expect(resolveLearner(request, " Alua Learner ")).resolves.toMatchObject({ uid: "learner-id" });
  expect(calls).toEqual([["/me", undefined], ["/auth/register", { method: "POST", body: { display_name: "Alua Learner" } }]]);
  for (const failure of [new ApiError(403, "forbidden"), new ApiError(401, "unauthorized"), new ApiError(429, "throttled")]) {
    let count = 0;
    await expect(resolveLearner(async () => { count++; throw failure; })).rejects.toBe(failure);
    expect(count).toBe(1);
  }
});

test("redirects cannot escape origin or loop into auth routes", () => {
  expect(safeReturnPath("/reading/cambridge-12?test=5")).toBe("/reading/cambridge-12?test=5");
  for (const path of ["https://evil.test", "//evil.test", "/\\evil.test", "/login?next=/login", "/register", "/\n/evil.test", "/%6cogin", "/register%2f", "/%2fevil.test", "/%5cevil.test", "/%00", "/%zz"]) {
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


test("parallel onboarding for one Firebase UID shares a request and failures stop until explicit retry", async () => {
  const calls: string[] = [];
  const failure = new ApiError(429, "registration_throttled", undefined, 30);
  let fail = true;
  const request: ReturnType<typeof createApiClient> = async (path) => {
    calls.push(path);
    await new Promise(resolve => setTimeout(resolve, 10));
    if (path === "/me") throw new ApiError(403, "identity_not_allowed");
    if (fail) throw failure;
    return {uid: "learner", email: null, display_name: "Learner"};
  };
  const results = await Promise.allSettled(Array.from({length: 8}, () => resolveLearner(request, null, "firebase-uid")));
  expect(results.every(r => r.status === "rejected" && r.reason === failure)).toBe(true);
  expect(calls).toEqual(["/me", "/auth/register"]);
  await new Promise(resolve => setTimeout(resolve, 50));
  expect(calls).toHaveLength(2);
  expect(authMessage(failure)).toContain("30 seconds");
  fail = false;
  await expect(resolveLearner(request, null, "firebase-uid")).resolves.toMatchObject({uid: "learner"});
  expect(calls).toEqual(["/me", "/auth/register", "/me", "/auth/register"]);
});

test("existing learner never registers and API failure never repeats registration", async () => {
  const calls: string[] = [];
  const existing: ReturnType<typeof createApiClient> = async path => {
    calls.push(path);
    return {uid: "existing", email: null, display_name: "Existing"};
  };
  await expect(resolveLearner(existing)).resolves.toMatchObject({uid: "existing"});
  expect(calls).toEqual(["/me"]);
  for (const status of [429, 503]) {
    calls.length = 0;
    await expect(resolveLearner(async path => {
      calls.push(path);
      throw new ApiError(path === "/me" ? 403 : status, path === "/me" ? "identity_not_allowed" : "failure");
    })).rejects.toMatchObject({status});
    expect(calls).toEqual(["/me", "/auth/register"]);
  }
});

test("proxy and API client retain Retry-After for real throttling without retrying mutation", async () => {
  const {createServer} = await import("node:http");
  const {proxyAlua} = await import("../src/lib/api/proxy");
  let requests = 0;
  const server = createServer((_request, response) => {
    requests++;
    response.writeHead(429, {"Content-Type": "application/json", "Retry-After": "45"});
    response.end(JSON.stringify({error: {code: "registration_throttled"}}));
  });
  await new Promise<void>(resolve => server.listen(0, "127.0.0.1", resolve));
  const address = server.address();
  if (!address || typeof address === "string") throw new Error("fixture unavailable");
  const oldBase = process.env.NEXT_PUBLIC_API_BASE_URL;
  process.env.NEXT_PUBLIC_API_BASE_URL = `http://127.0.0.1:${address.port}/api/v1`;
  try {
    const proxied = await proxyAlua(new Request("https://alua.study/api/alua/auth/register", {
      method: "POST", headers: {Authorization: "Bearer fixture"}, body: "{}",
    }), ["auth", "register"]);
    expect(proxied.status).toBe(429);
    expect(proxied.headers.get("retry-after")).toBe("45");
    await expect(createApiClient(async () => "fixture")("/auth/register", undefined, {method: "POST", body: {}}))
      .rejects.toMatchObject({status: 429, code: "registration_throttled", retryAfterSeconds: 45});
    expect(requests).toBe(2);
  } finally {
    server.closeAllConnections();
    await new Promise<void>(resolve => server.close(() => resolve()));
    if (oldBase === undefined) delete process.env.NEXT_PUBLIC_API_BASE_URL;
    else process.env.NEXT_PUBLIC_API_BASE_URL = oldBase;
  }
});

const learner = { uid: "backend-profile", email: null, display_name: "Learner" };

test("real /me HTTP 504 recovers, while terminal 401 keeps only the existing token-refresh retry", async () => {
  const { createServer } = await import("node:http");
  const calls: string[] = [];
  const forced: (boolean | undefined)[] = [];
  let unauthorized = false;
  const server = createServer((request, response) => {
    calls.push(request.url!);
    response.writeHead(unauthorized ? 401 : calls.length === 1 ? 504 : 200, { "Content-Type": "application/json" });
    response.end(JSON.stringify(unauthorized ? { error: { code: "unauthorized" } } : calls.length === 1 ? { error: { code: "timeout" } } : learner));
  });
  await new Promise<void>(resolve => server.listen(0, "127.0.0.1", resolve));
  const address = server.address();
  if (!address || typeof address === "string") throw new Error("fixture unavailable");
  const oldBase = process.env.NEXT_PUBLIC_API_BASE_URL;
  process.env.NEXT_PUBLIC_API_BASE_URL = `http://127.0.0.1:${address.port}/api/v1`;
  try {
    const client = createApiClient(async force => { forced.push(force); return "fixture"; });
    await expect(resolveLearner(client)).resolves.toEqual(learner);
    expect(calls).toEqual(["/api/v1/me", "/api/v1/me"]);
    unauthorized = true; calls.length = 0; forced.length = 0;
    await expect(resolveLearner(client)).rejects.toMatchObject({ status: 401 });
    expect(calls).toEqual(["/api/v1/me", "/api/v1/me"]);
    expect(forced).toEqual([false, true]);
  } finally {
    server.closeAllConnections();
    await new Promise<void>(resolve => server.close(() => resolve()));
    if (oldBase === undefined) delete process.env.NEXT_PUBLIC_API_BASE_URL;
    else process.env.NEXT_PUBLIC_API_BASE_URL = oldBase;
  }
});

for (const failure of [new ApiError(504, "timeout"), new ApiError(502, "upstream_unavailable"), new ApiError(503, "unavailable"), new ApiError(0, "network_error"), new ApiError(0, "timeout")]) {
  test(`safe /me recovers once from ${failure.status}/${failure.code}, sharing concurrent requests`, async () => {
    const calls: string[] = [];
    let retries = 0;
    const request: ReturnType<typeof createApiClient> = async path => {
      calls.push(path);
      if (calls.length === 1) throw failure;
      return learner;
    };
    const results = await Promise.all(Array.from({ length: 6 }, () => resolveLearner(request, null, "recovery-uid", { onRetry: () => { retries++; } })));
    expect(results).toEqual(Array(6).fill(learner));
    expect(calls).toEqual(["/me", "/me"]);
    expect(retries).toBe(1);
  });
}

test("persistent outage terminates with retained Firebase identity and no automatic provisioning", async () => {
  let count = 0;
  const h = sessionHarness(async () => { count++; throw new ApiError(504, "timeout"); }, "outage");
  await expect.poll(() => h.snapshot().status).toBe("error");
  expect(h.states.some(s => s.status === "loading" && s.retrying)).toBe(true);
  expect(h.states.some(s => s.status === "ready")).toBe(false);
  expect(h.snapshot()).toMatchObject({ user: { uid: "outage" }, profile: null });
  expect(h.auth.currentUser?.uid).toBe("outage");
  await new Promise(resolve => setTimeout(resolve, 400));
  expect(count).toBe(2);
});

test("Retry-After is a minimum wait; a cooldown outside the total budget requires explicit retry", async () => {
  let count = 0;
  const start = performance.now();
  await resolveLearner(async () => {
    if (++count === 1) throw new ApiError(503, "unavailable", undefined, 1);
    return learner;
  });
  expect(performance.now() - start).toBeGreaterThanOrEqual(990);
  expect(count).toBe(2);
  count = 0;
  const cooldown = ME_RECOVERY_TIMEOUT_MS / 1000 + 1;
  await expect(resolveLearner(async () => { count++; throw new ApiError(503, "unavailable", undefined, cooldown); })).rejects.toMatchObject({ retryAfterSeconds: cooldown });
  expect(count).toBe(1);
});

test("total /me deadline aborts a stalled transport without a retry or registration storm", async () => {
  let calls = 0;
  let signal: AbortSignal | undefined;
  await expect(resolveLearner(async (_path, active) => {
    calls++; signal = active;
    return new Promise(() => {});
  }, null, "stalled", { deadlineMilliseconds: 40 })).rejects.toMatchObject({ status: 0, code: "timeout" });
  expect(signal?.aborted).toBe(true);
  expect(calls).toBe(1);
  expect(ME_PROXY_TIMEOUT_MS).toBeLessThan(ME_CLIENT_TIMEOUT_MS);
  expect(2 * ME_CLIENT_TIMEOUT_MS + 350).toBeLessThan(ME_RECOVERY_TIMEOUT_MS);
});

test("UID switch during backoff cancels the old identity and authorizes only the new one", async () => {
  const calls: string[] = [];
  const h = sessionHarness(async path => {
    calls.push(`${h.auth.currentUser?.uid}:${path}`);
    if (h.auth.currentUser?.uid === "old") throw new ApiError(504, "timeout");
    return learner;
  }, "old");
  await expect.poll(() => h.snapshot().retrying).toBe(true);
  h.switchUser("new");
  await expect.poll(() => h.snapshot().status).toBe("ready");
  expect(h.snapshot().user?.uid).toBe("new");
  expect(h.signals[0]?.aborted).toBe(true);
  await new Promise(resolve => setTimeout(resolve, 400));
  expect(calls).toEqual(["old:/me", "new:/me"]);
});

test("logout during backoff cancels recovery and cannot publish a late authorized session", async () => {
  let calls = 0;
  const h = sessionHarness(async () => { calls++; throw new ApiError(504, "timeout"); }, "logout");
  await expect.poll(() => h.snapshot().retrying).toBe(true);
  await h.session.logout();
  await new Promise(resolve => setTimeout(resolve, 400));
  expect(h.snapshot()).toMatchObject({ status: "signed_out", user: null, profile: null });
  expect(h.signals[0]?.aborted).toBe(true);
  expect(calls).toBe(1);
});

test("late /me after a UID switch cannot override the newly authorized session", async () => {
  let finish!: (value: unknown) => void;
  let first = true;
  const h = sessionHarness(async () => {
    if (first) { first = false; return new Promise(resolve => { finish = resolve; }); }
    return learner;
  }, "late-old");
  await expect.poll(() => h.signals.length).toBe(1);
  h.switchUser("late-new");
  await expect.poll(() => h.snapshot().status).toBe("ready");
  finish({ ...learner, uid: "stale-profile" });
  await new Promise(resolve => setTimeout(resolve, 10));
  expect(h.snapshot()).toMatchObject({ user: { uid: "late-new" }, profile: learner });
});

for (const status of [401, 403]) {
  test(`${status} fails closed without transient retry, registration or navigation`, async () => {
    let calls = 0;
    const h = sessionHarness(async () => { calls++; throw new ApiError(status, "forbidden"); }, `denied-${status}`);
    await expect.poll(() => h.snapshot().status).toBe("error");
    expect(h.snapshot().profile).toBeNull();
    expect(h.states.some(s => s.status === "ready")).toBe(false);
    const form = formHarness(h.snapshot, "/history");
    form.render();
    expect(form.redirects).toEqual([]);
    expect(calls).toBe(1);
  });
}

test("restored Firebase session automatically navigates exactly once after backend authorization", async () => {
  let finish!: (value: unknown) => void;
  const h = sessionHarness(async () => new Promise(resolve => { finish = resolve; }), "restored-login");
  const form = formHarness(h.snapshot, "/history?tab=reading");
  form.render();
  expect(form.redirects).toEqual([]);
  await expect.poll(() => h.signals.length).toBe(1);
  finish(learner);
  await expect.poll(() => h.snapshot().status).toBe("ready");
  form.render(); form.render();
  expect(form.redirects).toEqual(["/history?tab=reading"]);
  for (const next of ["//evil.test", "/login?next=/login", "/register", "/%6cogin"]) {
    const sanitized = formHarness(h.snapshot, next);
    sanitized.render(); sanitized.render();
    expect(sanitized.redirects).toEqual(["/"]);
  }
});

test("password-to-Google linking stays on login after password authorization", async () => {
  let state: Session = { status: "signed_out", user: null, profile: null, generation: 0 };
  const form = formHarness(() => state, "/history", async () => {
    state = { status: "ready", user: { uid: "linking", email: null }, profile: learner, generation: 1 };
  });
  const toggle = elements(form.render()).find(e => e.type === "button" && e.props.children === "Connect Google safely");
  expect(toggle).toBeTruthy();
  (toggle!.props.onClick as () => void)();
  const loginForm = elements(form.render()).find(e => e.type === "form");
  await (loginForm!.props.onSubmit as (event: { preventDefault: () => void }) => Promise<void>)({ preventDefault: () => {} });
  form.render(); form.render();
  expect(state.status).toBe("ready");
  expect(form.redirects).toEqual([]);
});
