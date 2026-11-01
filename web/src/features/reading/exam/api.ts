import { createApiClient, ApiError } from "@/lib/api/client";
import { getIdToken } from "@/lib/firebase/client";
import { parseAttempt, parseExam } from "./parse";
export function readingApi(uid: string) { return createApiClient((force) => getIdToken(force, uid)); }
export async function getAttempt(id: string, uid: string, signal?: AbortSignal) {
  const attempt = parseAttempt(await readingApi(uid)(`/reading/attempts/${encodeURIComponent(id)}`, signal), true);
  if (attempt.id !== id) throw new ApiError(502, "unexpected_reading_response");
  return attempt;
}
export async function getExam(id: string, uid: string, signal?: AbortSignal) { return parseExam(await readingApi(uid)(`/reading/exams/${encodeURIComponent(id)}`, signal)); }
export function eventId() {
  if (typeof crypto.randomUUID === "function") return crypto.randomUUID();
  const b = crypto.getRandomValues(new Uint8Array(16));
  b[6] = (b[6]! & 15) | 64; b[8] = (b[8]! & 63) | 128;
  const hex = [...b].map((v) => v.toString(16).padStart(2, "0")).join("");
  return `${hex.slice(0,8)}-${hex.slice(8,12)}-${hex.slice(12,16)}-${hex.slice(16,20)}-${hex.slice(20)}`;
}
