import { ApiError } from "@/lib/api/client";

/** Keep the mutation ID after an unknown response so retry cannot create duplicates. */
export async function retakeTest(section: "listening" | "reading", uid: string, previousId: string, examId: string,
  create: (body: Record<string, unknown>) => Promise<unknown>): Promise<string> {
  const key = `alua:retake:${section}:${uid}:${previousId}`;
  let event = sessionStorage.getItem(key);
  if (!event) {
    event = crypto.randomUUID();
    sessionStorage.setItem(key, event);
  }
  const value = await create({ event_id: event, exam_id: examId, reuse_active: false, ...(section === "reading" ? { mode: "full_exam" } : {}) });
  const attempt = value as { id?: string; exam_id?: string; status?: string; answers?: Record<string, unknown> } | null;
  if (!attempt || !attempt.id || !/^[0-9a-f-]{36}$/i.test(attempt.id) || attempt.id === previousId || attempt.exam_id !== examId || attempt.status !== "in_progress" || !attempt.answers || Object.values(attempt.answers).some(answer => answer !== "")) {
    throw new ApiError(502, "unexpected_retake_response");
  }
  sessionStorage.removeItem(key);
  return attempt.id;
}
