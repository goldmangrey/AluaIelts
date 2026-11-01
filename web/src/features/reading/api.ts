import { ApiError, createApiClient } from "@/lib/api/client";
import { getIdToken } from "@/lib/firebase/client";
import type { ReadingCatalog, ReadingEntry } from "./contracts";

function object(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === "object" && !Array.isArray(value);
}
function positive(value: unknown): value is number { return Number.isSafeInteger(value) && Number(value) > 0; }
function strings(value: unknown): value is string[] { return Array.isArray(value) && value.every((v) => typeof v === "string"); }
function entry(value: unknown): value is ReadingEntry {
  return object(value) && typeof value.exam_id === "string" &&
    /^cambridge-\d{2}-test-\d{2}$/.test(value.exam_id) && positive(value.source_book) &&
    positive(value.source_test_number) && positive(value.test_ordinal) &&
    typeof value.enabled_for_private_practice === "boolean" &&
    ["ready", "needs_review", "blocked"].includes(String(value.content_status)) &&
    typeof value.not_fully_proofread === "boolean" && positive(value.question_count) &&
    positive(value.passage_count) && strings(value.in_progress_attempt_ids);
}
export function parseCatalog(value: unknown): ReadingCatalog {
  if (!object(value) || typeof value.dataset_version !== "string" || !Array.isArray(value.items)) {
    throw new ApiError(502, "unexpected_response");
  }
  const seen = new Set<number>();
  const exams = new Set<string>();
  const items = value.items.map((book: unknown) => {
    if (!object(book) || !positive(book.book_number) || seen.has(book.book_number) ||
        !Array.isArray(book.exams) || !book.exams.every(entry)) throw new ApiError(502, "unexpected_response");
    seen.add(book.book_number);
    for (const exam of book.exams) {
      if (exam.source_book !== book.book_number || exams.has(exam.exam_id) ||
          exam.exam_id !== `cambridge-${String(book.book_number).padStart(2, "0")}-test-${String(exam.source_test_number).padStart(2, "0")}`) {
        throw new ApiError(502, "unexpected_response");
      }
      exams.add(exam.exam_id);
    }
    return { book_number: book.book_number, exams: book.exams };
  });
  return { dataset_version: value.dataset_version, items };
}
export async function getReadingCatalog(signal?: AbortSignal): Promise<ReadingCatalog> {
  return parseCatalog(await createApiClient(getIdToken)("/reading/books", signal));
}
export function availableBooks(catalog: ReadingCatalog) {
  return catalog.items.map((book) => ({ ...book,
    exams: book.exams.filter((exam) => exam.enabled_for_private_practice && exam.content_status !== "blocked")
      .sort((a, b) => a.test_ordinal - b.test_ordinal),
  })).filter((book) => book.exams.length > 0).sort((a, b) => a.book_number - b.book_number);
}
