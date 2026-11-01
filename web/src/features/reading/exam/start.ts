import type { ReadingCatalog } from "../contracts";
import { ApiError } from "@/lib/api/client";
import { eventId } from "./api";
import { parseAttempt } from "./parse";
export interface CreateReadingAttempt { event_id: string; exam_id: string; mode: "full_exam"; reuse_active: true }
export async function findOrStart(examId: string, key: string, services: {
  catalog: () => Promise<ReadingCatalog>;
  create: (body: CreateReadingAttempt) => Promise<unknown>;
  storage: Pick<Storage, "getItem" | "setItem">;
}): Promise<string[]> {
  const catalog = await services.catalog();
  const entry = catalog.items.flatMap((b) => b.exams).find((e) => e.exam_id === examId);
  if (!entry?.enabled_for_private_practice || entry.content_status === "blocked") throw new ApiError(404, "reading_exam_unavailable");
  if (entry.in_progress_attempt_ids.length) return entry.in_progress_attempt_ids;
  const saved = services.storage.getItem(key);
  const id = saved && /^[0-9a-f-]{36}$/.test(saved) ? saved : eventId();
  services.storage.setItem(key, id); // A storage failure must stop before POST.
  const attempt = parseAttempt(await services.create({ event_id: id, exam_id: examId, mode: "full_exam", reuse_active: true }));
  if (attempt.exam_id !== examId) throw new ApiError(502, "unexpected_reading_response");
  return [attempt.id];
}
