import { ApiError, createApiClient } from "@/lib/api/client";
import { getIdToken } from "@/lib/firebase/client";
import { ME_RECOVERY_TIMEOUT_MS } from "@/lib/api/deadlines";

export interface LearnerProfile { uid: string; email: string | null; display_name: string | null }
function profile(value: unknown): LearnerProfile {
  if (!value || typeof value !== "object" || !("uid" in value) || typeof value.uid !== "string" || !value.uid ||
      !("email" in value) || !(value.email === null || typeof value.email === "string") ||
      !("display_name" in value) || !(value.display_name === null || typeof value.display_name === "string")) {
    throw new ApiError(502, "unexpected_response");
  }
  return { uid: value.uid, email: value.email, display_name: value.display_name };
}
export interface RecoveryOptions {
  signal?: AbortSignal;
  onRetry?: () => void;
  /** May shorten the overall /me deadline, never extend it. */
  deadlineMilliseconds?: number;
}
export async function loadLearner(displayName?: string | null, expectedUid?: string, options: RecoveryOptions = {}): Promise<LearnerProfile> {
  return resolveLearner(createApiClient((force) => getIdToken(force, expectedUid)), displayName, expectedUid, options);
}
const pendingLearners = new Map<string, { promise: Promise<LearnerProfile>; signal?: AbortSignal }>();
export function resolveLearner(request: ReturnType<typeof createApiClient>, displayName?: string | null, expectedUid?: string, options: RecoveryOptions = {}): Promise<LearnerProfile> {
  options.signal?.throwIfAborted();
  if (!expectedUid) return fetchLearner(request, displayName, options);
  const pending = pendingLearners.get(expectedUid);
  if (pending && !pending.signal?.aborted) return pending.promise;
  const promise = fetchLearner(request, displayName, options).finally(() => {
    if (pendingLearners.get(expectedUid)?.promise === promise) pendingLearners.delete(expectedUid);
  });
  pendingLearners.set(expectedUid, { promise, signal: options.signal });
  return promise;
}
async function recoverMe(request: ReturnType<typeof createApiClient>, options: RecoveryOptions): Promise<unknown> {
  options.signal?.throwIfAborted();
  const controller = new AbortController();
  const cancel = () => controller.abort(options.signal?.reason);
  options.signal?.addEventListener("abort", cancel, { once: true });
  const budget = Math.min(options.deadlineMilliseconds ?? ME_RECOVERY_TIMEOUT_MS, ME_RECOVERY_TIMEOUT_MS);
  const until = performance.now() + budget;
  const deadline = setTimeout(() => controller.abort(new ApiError(0, "timeout")), budget);
  let stopped!: () => void;
  const aborted = new Promise<never>((_, reject) => {
    stopped = () => reject(controller.signal.reason);
    controller.signal.addEventListener("abort", stopped, { once: true });
  });
  try {
    // One recovery retry of this safe GET only. Registration is outside this loop.
    for (let attempt = 0; attempt < 2; attempt++) {
      controller.signal.throwIfAborted();
      try {
        const value = await Promise.race([request("/me", controller.signal), aborted]);
        controller.signal.throwIfAborted();
        return value;
      } catch (error) {
        controller.signal.throwIfAborted();
        const transient = error instanceof ApiError && (
          [502, 503, 504].includes(error.status) ||
          error.status === 0 && ["network_error", "timeout"].includes(error.code)
        );
        const delay = Math.max(350, error instanceof ApiError ? (error.retryAfterSeconds ?? 0) * 1000 : 0);
        // A server cooldown longer than our remaining budget needs an explicit later retry.
        if (!transient || attempt !== 0 || delay >= until - performance.now()) throw error;
        options.onRetry?.();
        let pause: ReturnType<typeof setTimeout> | undefined;
        try { await Promise.race([new Promise<void>(resolve => { pause = setTimeout(resolve, delay); }), aborted]); }
        finally { clearTimeout(pause); }
      }
    }
    throw new ApiError(0, "timeout");
  } finally {
    clearTimeout(deadline);
    controller.signal.removeEventListener("abort", stopped);
    options.signal?.removeEventListener("abort", cancel);
  }
}
async function fetchLearner(request: ReturnType<typeof createApiClient>, displayName: string | null | undefined, options: RecoveryOptions): Promise<LearnerProfile> {
  try { return profile(await recoverMe(request, options)); }
  catch (error) {
    options.signal?.throwIfAborted();
    // Exact recovery contract used by iOS. Other 403s must never provision.
    if (!(error instanceof ApiError) || error.status !== 403 || error.code !== "identity_not_allowed") throw error;
    return profile(await request("/auth/register", options.signal, {
      method: "POST", body: { display_name: displayName?.trim() || null },
    }));
  }
}
