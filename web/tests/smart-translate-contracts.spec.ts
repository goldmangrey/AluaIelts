import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";
import ts from "typescript";
import { selectionContext, validInput, validateTranslation, canTranslateAttempt, parseTranslationOutput } from "../src/features/reading/translate/context";

const examples = [
  ["She is looking forward to studying abroad.", "forward", "looking forward to", "с нетерпением ждать"],
  ["I used to walk to school.", "used", "used to", "раньше ходил"],
  ["I am used to walking to school.", "used", "am used to", "привык ходить"],
  ["We take into account every detail.", "account", "take into account", "учитывать"],
  ["As a result of rain, we stayed home.", "result", "As a result of", "в результате"],
  ["The evidence is compelling.", "evidence", "evidence", "доказательства"],
];
for (const [sentence, selected, expression, translation] of examples as [string,string,string,string][]) {
  test(`validates exact contextual expression: ${expression}`, () => {
    const start = sentence.indexOf(selected);
    const input = selectionContext(sentence, start, start + selected.length)!;
    expect(validInput(input)).toBe(true);
    expect(validateTranslation({ expression, translation }, input)).toEqual({ expression, translation });
    expect(validateTranslation({ expression: "invented " + expression, translation }, input)).toBeNull();
  });
}
test("bounds context, rejects partial words, wrong occurrence and malformed output", () => {
  const text = "word ".repeat(500) + "evidence " + "word ".repeat(500);
  const start = text.indexOf("evidence");
  expect(selectionContext(text, start, start + 8)!.sentence.length).toBeLessThanOrEqual(600);
  expect(selectionContext("evidence", 1, 5)).toBeNull();
  const sentence = "We used to travel; now we are used to staying.";
  const selectedStart = sentence.lastIndexOf("used");
  const input = selectionContext(sentence, selectedStart, selectedStart + 4)!;
  expect(validateTranslation({ expression: "used to travel", translation: "раньше ездили" }, input)).toBeNull();
  expect(validateTranslation({ expression: "used to", translation: "x".repeat(300) }, input)).toBeNull();
});

function routeHarness() {
  let calls = 0, mode = "passage_practice", authenticated = true;
  let response = { expression: "looking forward to", translation: "с нетерпением ждать" };
  const input = selectionContext(examples[0]![0]!, 15, 22)!;
  const code = ts.transpileModule(readFileSync("src/app/api/translate/route.ts", "utf8"), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText;
  const exports: { POST?: (r: Request) => Promise<Response> } = {};
  const proxy = async (_r: Request, segments: string[]) => {
    if (!authenticated) return Response.json({}, { status: 401 });
    return Response.json(segments[0] === "me" ? { uid: "verified-learner" } : segments[1] === "books" ? { items: [{ exams: [{ exam_id: "cambridge-04-test-01", practice_policy_version: "private-practice-v1", enabled_for_private_practice: true, content_status: "needs_review" }] }] } : { mode, exam_id: "cambridge-04-test-01", exam: { passages: [{ id: "p1", content: [{ text: examples[0]![0] }] }] } });
  };
  const run = async (_model: string, args: Record<string, unknown>) => {
    calls++; expect(args.chat_template_kwargs).toEqual({ enable_thinking: false });
    expect(args.max_completion_tokens).toBe(160);
    return { choices: [{ message: { content: JSON.stringify(response) } }] };
  };
  new Function("require", "exports", code)((name: string) => name.includes("cloudflare") ? { getCloudflareContext: () => ({ env: { AI: { run } } }) } : name.includes("proxy") ? { proxyAlua: proxy } : { validInput, validateTranslation, canTranslateAttempt, parseTranslationOutput }, exports);
  const request = (patch = {}, token = "Bearer valid.firebase.signature") => exports.POST!(new Request("https://alua.test/api/translate", {
    method: "POST", headers: { Authorization: token }, body: JSON.stringify({ ...input, attemptId: "11111111-2222-4333-8444-555555555555", passageId: "p1", block: 0, ...patch }),
  }));
  return { request, calls: () => calls, mode: (v: string) => mode = v, auth: (v: boolean) => authenticated = v, output: (v: typeof response) => response = v };
}
test("server requires verified Firebase identity, practice ownership/context and validates AI", async () => {
  const h = routeHarness();
  expect((await h.request({}, "Bearer alua_dev_fake")).status).toBe(401);
  h.auth(false); expect((await h.request()).status).toBe(401); expect(h.calls()).toBe(0);
  h.auth(true); h.mode("official_exam"); expect((await h.request({ mode: "full_exam", translationAllowed: true })).status).toBe(403); expect(h.calls()).toBe(0);
  h.mode("full_exam"); expect((await h.request()).status).toBe(200);
  h.mode("passage_practice"); expect((await h.request({ sentence: "fabricated", selected: "fabricated", start: 0, end: 10 })).status).toBe(400);
  h.output({ expression: "look forward to", translation: "ждать" }); expect((await h.request()).status).toBe(502);
  h.output({ expression: "looking forward to", translation: "с нетерпением ждать" });
  const result = await h.request(); expect(result.status).toBe(200); expect(result.headers.get("cache-control")).toContain("no-store");
  expect(await result.json()).toEqual({ expression: "looking forward to", translation: "с нетерпением ждать" });
});
test("server limits requests and body size before AI", async () => {
  const h = routeHarness();
  expect((await h.request({ sentence: "x".repeat(5000) })).status).toBe(413);
  for (let i = 0; i < 12; i++) expect((await h.request()).status).toBe(200);
  expect((await h.request()).status).toBe(429); expect(h.calls()).toBe(12);
});

test("translation allows existing Start test mode only under the known private server policy", () => {
  const attempt = { mode: "full_exam", exam_id: "cambridge-04-test-01" };
  const entry = { exam_id: attempt.exam_id, practice_policy_version: "private-practice-v1", enabled_for_private_practice: true, content_status: "needs_review" };
  const catalog = (e: unknown) => ({ items: [{ exams: [e] }] });
  expect(canTranslateAttempt(attempt, catalog(entry))).toBe(true);
  expect(canTranslateAttempt({ ...attempt, mode: "passage_practice" }, catalog(entry))).toBe(true);
  for (const mode of ["official_exam", "restricted", "future", null]) expect(canTranslateAttempt({ ...attempt, mode }, catalog(entry))).toBe(false);
  for (const patch of [{ practice_policy_version: "official-v1" }, { practice_policy_version: undefined }, { enabled_for_private_practice: false }, { content_status: "blocked" }, { exam_id: "other" }]) expect(canTranslateAttempt(attempt, catalog({ ...entry, ...patch }))).toBe(false);
  expect(canTranslateAttempt(attempt, null)).toBe(false);
});

test("binding output formats retain strict verbatim quote and offset validation", () => {
  const sentence = "She is looking forward to studying abroad.";
  const input = { sentence, selected: "forward", start: 15, end: 22 };
  const result = { expression: "looking forward to", translation: "с нетерпением ждать" };
  const json = JSON.stringify(result);
  for (const output of [{ choices: [{ message: { content: json } }] }, { response: "```json\n" + json + "\n```" }, { response: result }, { choices: [{ message: { content: [{ type: "text", text: json }] } }] }]) expect(validateTranslation(parseTranslationOutput(output), input)).toEqual(result);
  expect(parseTranslationOutput({ response: "Explanation " + json })).toBeNull();
  expect(validateTranslation(parseTranslationOutput({ response: JSON.stringify({ ...result, expression: "look forward to" }) }), input)).toBeNull();
  expect(validInput({ ...input, end: 999 })).toBe(false);
  const multiline = "She is looking\nforward to studying abroad.";
  const start = multiline.indexOf("forward");
  expect(selectionContext(multiline, start, start + 7)?.sentence).toBe(multiline);
});
