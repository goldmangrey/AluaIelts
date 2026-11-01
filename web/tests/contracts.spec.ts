import { test, expect } from "@playwright/test";
import { availableBooks, parseCatalog } from "../src/features/reading/api";
import { createApiClient, ApiError } from "../src/lib/api/client";

// Boundary fixtures only: never imported by the application or served as content.
function entry(book: number, test: number, ordinal: number, enabled = true) {
  return { exam_id: `cambridge-${String(book).padStart(2, "0")}-test-${String(test).padStart(2, "0")}`,
    source_book: book, source_test_number: test, test_ordinal: ordinal,
    enabled_for_private_practice: enabled, content_status: "needs_review", not_fully_proofread: true,
    question_count: 40, passage_count: 3, in_progress_attempt_ids: [] };
}

test("availability comes from server, source test number survives ordering", () => {
  const catalog = parseCatalog({ dataset_version: "1.0.0", items: [
    { book_number: 4, exams: [entry(4, 1, 1, false)] },
    { book_number: 12, exams: [entry(12, 6, 2), entry(12, 5, 1), { ...entry(12, 7, 3), content_status: "blocked" }] },
  ] });
  expect(availableBooks(catalog).map((b) => b.book_number)).toEqual([12]);
  expect(availableBooks(catalog)[0]?.exams.map((e) => e.source_test_number)).toEqual([5, 6]);
});

test("malformed, mismatched, duplicate and missing availability fail closed", () => {
  const valid = entry(12, 5, 1);
  for (const exams of [
    [{ ...valid, source_book: 18 }], [{ ...valid, enabled_for_private_practice: "true" }],
    [valid, valid], [{ ...valid, exam_id: "javascript:alert(1)" }],
    [{ ...valid, question_count: 0 }], [{ ...valid, content_status: "unknown" }],
  ]) {
    expect(() => parseCatalog({ dataset_version: "1", items: [{ book_number: 12, exams }] })).toThrow(ApiError);
  }
  expect(() => parseCatalog({ items: [] })).toThrow(ApiError);
});

test("one token refresh on 401; no retry of forbidden or malformed JSON", async () => {
  const oldBase = process.env.NEXT_PUBLIC_API_BASE_URL;
  process.env.NEXT_PUBLIC_API_BASE_URL = "http://localhost:8000/api/v1";
  const original = globalThis.fetch;
  try {
    let count = 0;
    const refresh: boolean[] = [];
    globalThis.fetch = async (_input, init) => {
      count++;
      expect(init?.cache).toBe("no-store");
      expect(init?.redirect).toBe("error");
      return count === 1 ? new Response("", { status: 401 }) : Response.json({ items: [] });
    };
    await expect(createApiClient(async (force) => { refresh.push(!!force); return "test-token"; })("/reading/books")).resolves.toEqual({ items: [] });
    expect(count).toBe(2); expect(refresh).toEqual([false, true]);
    count = 0;
    globalThis.fetch = async () => { count++; return Response.json({ error: { code: "identity_not_allowed" } }, { status: 403 }); };
    await expect(createApiClient(async () => "test-token")("/reading/books")).rejects.toMatchObject({ status: 403, code: "identity_not_allowed" });
    expect(count).toBe(1);
    globalThis.fetch = async () => new Response("<html>gateway</html>");
    await expect(createApiClient(async () => "test-token")("/reading/books")).rejects.toMatchObject({ code: "unexpected_response" });
    let called = false;
    globalThis.fetch = async () => { called = true; return Response.json({}); };
    await expect(createApiClient(async () => null)("/reading/books")).rejects.toMatchObject({ status: 401 });
    expect(called).toBe(false);
  } finally {
    globalThis.fetch = original;
    if (oldBase === undefined) delete process.env.NEXT_PUBLIC_API_BASE_URL;
    else process.env.NEXT_PUBLIC_API_BASE_URL = oldBase;
  }
});

test("cancellation while token is pending never sends a request", async () => {
  const oldBase = process.env.NEXT_PUBLIC_API_BASE_URL;
  process.env.NEXT_PUBLIC_API_BASE_URL = "http://localhost:8000/api/v1";
  const controller = new AbortController();
  try {
    const pending = createApiClient(() => new Promise<string>(() => {}))("/reading/books", controller.signal);
    controller.abort();
    await expect(pending).rejects.toMatchObject({ name: "AbortError" });
  } finally {
    if (oldBase === undefined) delete process.env.NEXT_PUBLIC_API_BASE_URL;
    else process.env.NEXT_PUBLIC_API_BASE_URL = oldBase;
  }
});
