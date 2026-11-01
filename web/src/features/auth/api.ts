import { ApiError, createApiClient } from "@/lib/api/client";
import { getIdToken } from "@/lib/firebase/client";

export interface LearnerProfile { uid: string; email: string | null; display_name: string | null }
function profile(value: unknown): LearnerProfile {
  if (!value || typeof value !== "object" || !("uid" in value) || typeof value.uid !== "string" || !value.uid ||
      !("email" in value) || !(value.email === null || typeof value.email === "string") ||
      !("display_name" in value) || !(value.display_name === null || typeof value.display_name === "string")) {
    throw new ApiError(502, "unexpected_response");
  }
  return { uid: value.uid, email: value.email, display_name: value.display_name };
}
export async function loadLearner(displayName?: string | null, expectedUid?: string): Promise<LearnerProfile> {
  return resolveLearner(createApiClient((force) => getIdToken(force, expectedUid)), displayName);
}
export async function resolveLearner(request: ReturnType<typeof createApiClient>, displayName?: string | null): Promise<LearnerProfile> {
  try { return profile(await request("/me")); }
  catch (error) {
    // Exact recovery contract used by iOS. Other 403s must never provision.
    if (!(error instanceof ApiError) || error.status !== 403 || error.code !== "identity_not_allowed") throw error;
    return profile(await request("/auth/register", undefined, {
      method: "POST", body: { display_name: displayName?.trim() || null },
    }));
  }
}
