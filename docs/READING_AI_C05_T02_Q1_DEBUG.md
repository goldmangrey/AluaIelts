# Targeted local debug — C05 Test 2 Q1

2026-11-11. Existing local stack and signed-in local account. No production
configuration, answer keys, grading, commits, pushes or deployments changed.
A separate empty local smoke attempt was created/submitted through the UI;
existing attempts were not edited.

## Findings

The previously open browser tab and existing failed provider log were **C04 Test 1**,
not C05 Test 2. That earlier Cloudflare call ran for 5555 ms and failed
`invalid_output`; the old log did not retain its validation subtype. Its exact
schema/candidate/prose failure cannot be reconstructed honestly from that log.
No failed C05 request existed in the inspected local logs before this debug run.

Fresh actual browser requests for **C05 Test 2 Q1 and Q3** followed:
`/api/reading/review` → FastAPI owner-scoped review → `/api/reading/explain`
→ authenticated FastAPI frozen context → real Cloudflare AI → task validation
→ independent backend validation/cache → UI.

Both contexts: `unavailable_reason=null`, 42 owned candidates, correct passage 1
“Bakelite — The birth of modern plastics”, snapshot matches the current canonical
exam on creation. Saved keys: Q1 `candlewax`, Q3 `chemistry`. Subsequent context and
cache checks use the frozen snapshot, not a replacement canonical exam.

Groq had no local key and made no HTTP model call. Cloudflare
`@cf/google/gemma-4-26b-a4b-it` succeeded (1994 ms Q1, 4139 ms Q3).
Gemini/OpenRouter were excluded by the existing sensitive-task policy.

Both responses: substantive Russian explanations, `evidence_status=found`, one
owned exact anchor each. Q1 cites the candlewax/melting sentence; Q3 cites progress
in chemistry. Actual Show in passage actions focused and visibly highlighted the
correct exact sentences. Both saved cache entries independently revalidated with
matching fingerprints and 0600 permissions.

**C05 Q1 root cause: UNKNOWN / not reproduced.** No observed timeout, invalid JSON,
rejected quote or grounding failure for either new request. Legacy
`key_not_grounded` / `blank_context_not_grounded` heuristics are not present in
the current candidate validator. No evidence check was relaxed for this debug.

## Minimal changes / verification

- Worker route logs bounded validation category (schema, candidate, quote, etc.)
  or model-declared unavailable, without source/model content or identifiers.
- Exact-citation assurance is shown only when evidence is present and found.
- 20 Reading AI contract checks passed; missing-evidence disclaimer checks passed
  in desktop Chromium and mobile WebKit. TypeScript and targeted ESLint passed.
- Live Q1 **PASS**; live Q3 **PASS**. Earlier C04 failure subtype remains unknown.
