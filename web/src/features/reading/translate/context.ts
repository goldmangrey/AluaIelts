export interface TranslationInput { sentence: string; selected: string; start: number; end: number }
export interface Translation { expression: string; translation: string }
const english = /^[A-Za-z]+(?:['’\-][A-Za-z]+)*(?:\s+[A-Za-z]+(?:['’\-][A-Za-z]+)*)*$/;
export function validInput(value: unknown): value is TranslationInput {
  if (!value || typeof value !== "object") return false;
  const v = value as TranslationInput;
  return typeof v.sentence === "string" && v.sentence.length <= 600 &&
    typeof v.selected === "string" && v.selected.length <= 100 && english.test(v.selected) &&
    Number.isInteger(v.start) && Number.isInteger(v.end) && v.start >= 0 && v.end > v.start && v.end <= v.sentence.length &&
    v.sentence.slice(v.start, v.end) === v.selected &&
    !/[A-Za-z'’\-]/.test(v.sentence[v.start - 1] ?? "") && !/[A-Za-z'’\-]/.test(v.sentence[v.end] ?? "");
}
/** UTF-16 offsets match DOM Range and String.slice. Long sentences get a bounded window. */
export function selectionContext(text: string, start: number, end: number): TranslationInput | null {
  const selected = text.slice(start, end);
  let left = start, right = end;
  while (left > 0 && !/[.!?]/.test(text[left - 1]!)) left--;
  while (right < text.length && !/[.!?]/.test(text[right]!)) right++;
  if (right < text.length) right++;
  left = Math.max(left, start - 240);
  right = Math.min(right, left + 600);
  const input = { sentence: text.slice(left, right), selected, start: start - left, end: end - left };
  return validInput(input) ? input : null;
}
export function validateTranslation(value: unknown, input: TranslationInput): Translation | null {
  if (!value || typeof value !== "object") return null;
  const v = value as Translation;
  if (typeof v.expression !== "string" || !v.expression.trim() || v.expression.length > 160 ||
      typeof v.translation !== "string" || !v.translation.trim() || v.translation.length > 240 ||
      !/[А-Яа-яЁё]/.test(v.translation) || /[\x00-\x1f<>]/.test(v.translation)) return null;
  // Validate the actual occurrence covering the selection, not another matching word.
  let from = 0;
  while (from <= input.start) {
    const index = input.sentence.indexOf(v.expression, from);
    if (index < 0) break;
    const end = index + v.expression.length;
    if (index <= input.start && end >= input.end &&
        !/[A-Za-z'’\-]/.test(input.sentence[index - 1] ?? "") && !/[A-Za-z'’\-]/.test(input.sentence[end] ?? ""))
      return { expression: v.expression, translation: v.translation.trim() };
    from = index + 1;
  }
  return null;
}

/** Known private Reading policy only. Both UI and API use server-owned attempt/catalog data. */
export function canTranslateAttempt(attempt: { mode: unknown; exam_id: unknown }, catalog: unknown): boolean {
  if (attempt.mode !== "full_exam" && attempt.mode !== "passage_practice") return false;
  if (typeof attempt.exam_id !== "string" || !catalog || typeof catalog !== "object" || !("items" in catalog) || !Array.isArray(catalog.items)) return false;
  const entries = catalog.items.flatMap((book: unknown) => {
    if (!book || typeof book !== "object" || !("exams" in book) || !Array.isArray(book.exams)) return [];
    return book.exams.filter((entry: unknown) => !!entry && typeof entry === "object" && "exam_id" in entry && entry.exam_id === attempt.exam_id);
  });
  if (entries.length !== 1) return false;
  const entry = entries[0];
  return entry.practice_policy_version === "private-practice-v1" && entry.enabled_for_private_practice === true &&
    (entry.content_status === "ready" || entry.content_status === "needs_review");
}

/** Accept documented binding envelopes and whole JSON fences; never guess JSON from prose. */
export function parseTranslationOutput(output: unknown): unknown {
  const object = (value: unknown): value is Record<string, unknown> => !!value && typeof value === "object" && !Array.isArray(value);
  let raw: unknown = output;
  if (object(output)) {
    const choice = Array.isArray(output.choices) ? output.choices[0] : undefined;
    raw = object(choice) && object(choice.message) ? choice.message.content : output.response ?? output;
  }
  if (Array.isArray(raw)) {
    if (!raw.every(part => object(part) && (part.type === "text" || part.type === "output_text") && typeof part.text === "string")) return null;
    raw = raw.map(part => part.text).join("");
  }
  if (object(raw)) return typeof raw.expression === "string" && typeof raw.translation === "string" && raw.expression.length <= 160 && raw.translation.length <= 240 ? raw : null;
  if (typeof raw !== "string" || raw.length > 1600) return null;
  const text = raw.trim();
  const fenced = /^```(?:json)?\s*([\s\S]*?)\s*```$/i.exec(text);
  try { return JSON.parse(fenced ? fenced[1]! : text); } catch { return null; }
}
