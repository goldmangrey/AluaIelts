/** Accept only same-origin paths; never forward credentials to another host. */
export function safeReturnPath(value: string | null): string {
  if (!value || !value.startsWith("/") || value.startsWith("//") || /[\\\x00-\x20]/.test(value)) return "/";
  try {
    const parsed = new URL(value, "https://alua.invalid");
    if (parsed.origin !== "https://alua.invalid" || /^\/(login|register|forgot-password)(\/|$)/.test(parsed.pathname)) return "/";
    return parsed.pathname + parsed.search + parsed.hash;
  } catch { return "/"; }
}
