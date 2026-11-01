/** Wire names from reading/catalog.py + service.library, verified 2026-11-01.
 * Reading GET responses have no response_model in OpenAPI; validate at runtime.
 * Keep this subset aligned with backend; never import dataset or answer keys.
 */
export interface ReadingEntry {
  exam_id: string;
  source_book: number;
  source_test_number: number;
  test_ordinal: number;
  enabled_for_private_practice: boolean;
  content_status: "ready" | "needs_review" | "blocked";
  not_fully_proofread: boolean;
  question_count: number;
  passage_count: number;
  in_progress_attempt_ids: string[];
}
export interface ReadingBook { book_number: number; exams: ReadingEntry[] }
export interface ReadingCatalog { dataset_version: string; items: ReadingBook[] }
