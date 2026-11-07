import { ApiError } from "@/lib/api/client";
export function readingMessage(error: unknown): string {
  if (!(error instanceof ApiError)) return "Couldn’t open or save this test. Check your connection and browser storage, then try again.";
  if (error.status === 401) return "Your session has expired. Log in again to continue.";
  if (error.status === 403) return "This account doesn’t have access to this test.";
  if(error.status===422)return "The server rejected this request. Your answers are retained. You can edit and retry Finish after the frontend and backend contracts match.";
  if (error.status === 404) return "This test or attempt is unavailable. It may not belong to this account.";
  if (error.code === "reading_private_content") return "This content failed a security check. The exam cannot be opened.";
  if (error.code === "unsupported_reading_format") return "This question format is not supported. The test cannot be opened safely.";
  if (error.code === "reading_asset_missing") return "A required task image is missing. Try again or choose another test.";
  if (error.code === "reading_attempt_completed") return "This attempt is no longer editable. Unsaved answers remain on this page. Open the result to see the server-confirmed outcome.";
  if(error.code==="reading_final_snapshot_changed")return "Answers changed in another session. Return to the test and review the merged answers before finishing.";
  if(error.code==="reading_final_snapshot_mismatch")return "Submission not confirmed. The server result differs from this device’s final answers; the local draft is retained.";
  if (error.code === "reading_version_conflict" || error.status === 409) return "Progress has changed in another session. Your unsaved answers are kept on this page; automatic saving is paused. Do not refresh.";
  if (error.code === "timeout") return "The connection is taking too long. Your current answers remain on this page. Try again.";
  if (error.code === "unexpected_reading_response") return "The test data could not be read safely. Please try again.";
  if (error.status >= 500) return "Reading is temporarily unavailable. Please try again.";
  return "Couldn’t connect to Reading. Your current answers remain on this page. Please try again.";
}
