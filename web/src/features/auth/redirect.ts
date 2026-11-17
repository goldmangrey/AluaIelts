/** Accept only same-origin paths; never forward credentials to another host. */
export function safeReturnPath(value: string | null): string {
  if (!value || !value.startsWith("/") || value.startsWith("//") || /[\\\x00-\x20]/.test(value)) return "/";
  try {
    const parsed = new URL(value, "https://alua.invalid");
    const pathname = decodeURIComponent(parsed.pathname);
    if (parsed.origin !== "https://alua.invalid" || pathname.startsWith("//") || /[\\\x00-\x20]/.test(pathname) ||
        /^\/(login|register|forgot-password)(\/|$)/.test(pathname)) return "/";
    return parsed.pathname + parsed.search + parsed.hash;
  } catch { return "/"; }
}
