import { ApiError } from "@/lib/api/client";
import { questionTypes, allQuestions, type Exam, type Attempt, type Block, type Constraints, type Option, type Segment, type Group, type Question } from "./models";
function fail(code = "unexpected_reading_response"): never { throw new ApiError(502, code); }
function obj(v: unknown): Record<string, unknown> { if (!v || typeof v !== "object" || Array.isArray(v)) fail(); return v as Record<string, unknown>; }
function text(v: unknown): string { if (typeof v !== "string") fail(); return v; }
function num(v: unknown, min = 1): number { if (typeof v !== "number" || !Number.isSafeInteger(v) || v < min) fail(); return v; }
function bool(v: unknown): boolean { if (typeof v !== "boolean") fail(); return v; }
function arr<T>(v: unknown, parse: (v: unknown) => T): T[] { if (!Array.isArray(v)) fail(); return v.map(parse); }
function choice<T extends string>(v: unknown, options: readonly T[]): T { if (!options.includes(v as T)) fail("unsupported_reading_format"); return v as T; }
function constraints(v: unknown): Constraints { const o = obj(v); return { max_words: o.max_words === null ? null : num(o.max_words), allow_number: bool(o.allow_number), allowed_values: arr(o.allowed_values, text), reuse_allowed: bool(o.reuse_allowed), selection_count: o.selection_count === null ? null : num(o.selection_count) }; }
function option(v: unknown): Option { const o = obj(v); return { label: text(o.label), text: text(o.text) }; }
function segment(v: unknown): Segment { const o = obj(v); if (o.type === "text") return { type: "text", text: text(o.text) }; if (o.type === "blank") return { type: "blank", number: num(o.number) }; return fail("unsupported_reading_format"); }
function block(v: unknown): Block {
  const o = obj(v);
  switch (o.type) {
    case "rich_text": return { type: o.type, segments: arr(o.segments, segment) };
    case "heading": return { type: o.type, text: text(o.text) };
    case "image": return { type: o.type, asset_id: text(o.asset_id), alt: text(o.alt) };
    case "list": return { type: o.type, items: arr(o.items, (item) => arr(item, segment)) };
    case "table": return { type: o.type, columns: arr(o.columns, text), rows: arr(o.rows, (row) => arr(row, (cell) => ({ segments: arr(obj(cell).segments, segment) }))) };
    default: return fail("unsupported_reading_format");
  }
}
function question(v: unknown): Question { const o = obj(v); return { id: text(o.id), group_id: text(o.group_id), number: num(o.number), type: choice(o.type, questionTypes), prompt: text(o.prompt), answer_input_type: choice(o.answer_input_type, ["text", "boolean", "single_select", "multi_select"]), options: arr(o.options, option), constraints: constraints(o.constraints) }; }
function group(v: unknown): Group {
  const o = obj(v);
  return { id: text(o.id), type: choice(o.type, questionTypes), instructions: text(o.instructions), question_numbers: arr(o.question_numbers, (n) => num(n)), options: arr(o.options, option), content_blocks: arr(o.content_blocks, block), assets: arr(o.assets, (v) => { const a = obj(v); return { id: text(a.id), mime_type: text(a.mime_type), width: num(a.width), height: num(a.height), sha256: text(a.sha256) }; }), constraints: constraints(o.constraints), questions: arr(o.questions, question), representation: choice(o.representation, ["structured_text", "source_image_with_inputs"]) };
}
function noKeys(v: unknown) {
  if (!v || typeof v !== "object") return;
  for (const [key, value] of Object.entries(v)) {
    if (["accepted_answers", "correct_answer", "canonical_answer", "answer_key", "answer_keys", "answer_key_hash"].includes(key)) fail("reading_private_content");
    noKeys(value);
  }
}
export function parseExam(v: unknown): Exam {
  noKeys(v); const o = obj(v);
  const exam: Exam = { id: text(o.id), dataset_version: text(o.dataset_version), source_book: num(o.source_book), source_test_number: num(o.source_test_number), duration_seconds: num(o.duration_seconds), question_count: num(o.question_count), passages: arr(o.passages, (v) => { const p = obj(v); return { id: text(p.id), number: num(p.number), title: text(p.title), subtitle: p.subtitle === null ? null : text(p.subtitle), content: arr(p.content, (v) => { const b = obj(v); return { type: choice(b.type, ["paragraph", "heading"]), text: text(b.text), label: b.label === null ? null : text(b.label) }; }), question_groups: arr(p.question_groups, group), question_numbers: arr(p.question_numbers, (n) => num(n)) }; }) };
  const questions = allQuestions(exam);
  const groups = exam.passages.flatMap((p) => p.question_groups);
  if (new Set(groups.map((g) => g.id)).size !== groups.length) fail();
  if (!exam.passages.length || exam.passages.length > 3 || questions.length !== exam.question_count || questions.length > 40 || new Set(questions.map((q) => q.id)).size !== questions.length || new Set(questions.map((q) => q.number)).size !== questions.length || new Set(exam.passages.map((p) => p.id)).size !== exam.passages.length || new Set(exam.passages.map((p) => p.number)).size !== exam.passages.length) fail();
  for (const p of exam.passages) {
    const qs = p.question_groups.flatMap((g) => g.questions);
    if (!p.content.length || !qs.length || p.number > 3 || JSON.stringify(p.question_numbers) !== JSON.stringify(qs.map((q) => q.number))) fail();
    for (const g of p.question_groups) {
      if (!g.questions.length || JSON.stringify(g.question_numbers) !== JSON.stringify(g.questions.map((q) => q.number))) fail();
      for (const q of g.questions) if (q.group_id !== g.id || q.type !== g.type || q.number > 40) fail();
      const known = new Set(g.question_numbers);
      const checkSegments = (segs: Segment[]) => { for (const s of segs) if (s.type === "blank" && !known.has(s.number)) fail(); };
      for (const b of g.content_blocks) {
        if (b.type === "rich_text") checkSegments(b.segments);
        if (b.type === "list") b.items.forEach(checkSegments);
        if (b.type === "table") b.rows.forEach((r) => r.forEach((c) => checkSegments(c.segments)));
        if (b.type === "image" && !g.assets.some((a) => a.id === b.asset_id)) fail("reading_asset_missing");
      }
      if (g.representation === "source_image_with_inputs" && !g.assets.length) fail("reading_asset_missing");
    }
  }
  return exam;
}
export function parseAttempt(v: unknown, requireExam = false): Attempt {
  const o = obj(v); const state = obj(o.state);
  const answers = Object.fromEntries(Object.entries(obj(o.answers)).map(([k, v]) => [k, text(v)]));
  const a: Attempt = { id: text(o.id), exam_id: text(o.exam_id), mode: choice(o.mode, ["full_exam", "passage_practice"]), status: choice(o.status, ["in_progress", "submitted", "expired"]), version: num(o.version, 0), content_hash: text(o.content_hash), server_now: text(o.server_now), deadline_at: o.deadline_at === null ? null : text(o.deadline_at), answers, state: { current_passage: num(state.current_passage), checked_question_ids: arr(state.checked_question_ids, text) }, not_fully_proofread: bool(o.not_fully_proofread) };
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(a.id)) fail();
  if (!Number.isFinite(Date.parse(a.server_now)) || (a.deadline_at !== null && !Number.isFinite(Date.parse(a.deadline_at))) || (a.mode === "full_exam" && !a.deadline_at)) fail();
  if(o.started_at!==undefined)a.started_at=text(o.started_at);
  if(o.submitted_at!==undefined)a.submitted_at=o.submitted_at===null?null:text(o.submitted_at);
  if (o.mutation_applied !== undefined) a.mutation_applied = bool(o.mutation_applied);
  if (o.exam !== undefined) { a.exam = parseExam(o.exam); if (a.exam.id !== a.exam_id) fail(); const ids = new Set(allQuestions(a.exam).map((q) => q.id)); if (Object.keys(answers).some((id) => !ids.has(id))) fail(); }
  if (a.mode === "full_exam" && a.status === "in_progress") noKeys({ ...o, answers: undefined });
  if (a.exam && a.mode === "full_exam" && (a.exam.question_count !== 40 || a.exam.passages.length !== 3)) fail();
  if (requireExam && !a.exam) fail();
  return a;
}
