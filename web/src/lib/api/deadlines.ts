// Preserve existing per-request limits: the proxy settles before the client deadline.
// Two /me attempts plus a short backoff fit in a separate finite recovery budget.
export const ME_PROXY_TIMEOUT_MS = 12_000;
export const ME_CLIENT_TIMEOUT_MS = 15_000;
export const ME_RECOVERY_TIMEOUT_MS = 31_000;
