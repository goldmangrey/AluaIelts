"use client";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useRef, useState } from "react";
import { getFirebaseAuth } from "@/lib/firebase/client";
import { withTimeout } from "@/lib/timeout";
import { authenticate, logout, retrySession, useSession } from "./session";
import { authMessage } from "./messages";
import { safeReturnPath } from "./redirect";

export function AuthForm({ mode }: { mode: "login" | "register" | "reset" }) {
  const session = useSession();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [show, setShow] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sent, setSent] = useState(false);
  const destination = safeReturnPath(useSearchParams().get("next"));
  const locked = useRef(false);
  const pending = busy || session.status === "loading";
  const register = mode === "register";
  const title = mode === "reset" ? "Reset password." : register ? "Create account." : "Log in.";
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (locked.current) return;
    locked.current = true; setBusy(true); setError(null);
    try {
      if (mode === "reset") {
        try {
          const auth = await getFirebaseAuth();
          const { sendPasswordResetEmail } = await import("firebase/auth");
          // Default Firebase hosted action handler; no untrusted/LAN continue URL.
          await withTimeout(sendPasswordResetEmail(auth, email.trim()));
        } catch (failure) {
          if (!(failure && typeof failure === "object" && "code" in failure && failure.code === "auth/user-not-found")) throw failure;
        }
        setSent(true);
      } else {
        await authenticate(register ? "register" : "login", email, password, name);
        setPassword(""); router.replace(destination); router.refresh();
      }
    } catch (failure) { setError(authMessage(failure)); }
    finally { locked.current = false; setBusy(false); }
  }
  async function recover() {
    if (locked.current) return;
    locked.current = true; setBusy(true); setError(null);
    try { await retrySession(); router.replace(destination); router.refresh(); }
    catch (failure) { setError(authMessage(failure)); }
    finally { locked.current = false; setBusy(false); }
  }
  const query = `?next=${encodeURIComponent(destination)}`;
  return <section className="auth-shell"><p className="eyebrow">Your Alua account</p><h1>{title}</h1>
    <p className="subtitle">{mode === "reset" ? "We’ll help you get back to your account." : "Continue your IELTS practice."}</p>
    {mode !== "reset" && session.user ? <div className="auth-form">
      <p className="small-note">Signed in as {session.user.email ?? "your Alua account"}.</p>
      {session.status === "error" && <p role="alert" className="form-error">{authMessage(session.error)} Your sign-in is saved. Retry account setup without creating another account.</p>}
      {session.status === "loading" && <p role="status">Preparing your Alua profile…</p>}
      <button className="button" disabled={busy || session.status === "loading"} onClick={() => { if (session.status === "ready") router.replace(destination); else void recover(); }}>
        {busy ? "Please wait…" : session.status === "ready" ? "Continue" : "Retry account setup"}
      </button>
      <button className="text-button" disabled={busy} onClick={async () => { try { await logout(); } catch (failure) { setError(authMessage(failure)); } }}>Use another account</button>
    </div> : sent ? <div className="auth-form" role="status"><h2>Check your inbox.</h2>
      <p className="small-note">If an account exists for this email, you’ll receive password reset instructions. Check your spam folder too.</p>
      <Link className="text-link" href={`/login${query}`}>Back to log in →</Link>
    </div> : <form className="auth-form" onSubmit={submit} aria-busy={busy}>
      {register && <label className="form-field">Name<input autoComplete="name" value={name} onChange={(e) => setName(e.target.value)} required maxLength={80} disabled={pending} /></label>}
      <label className="form-field">Email<input type="email" autoComplete="email" autoCapitalize="none" spellCheck={false} value={email} onChange={(e) => setEmail(e.target.value)} required maxLength={254} disabled={pending} /></label>
      {mode !== "reset" && <div className="form-field"><label htmlFor="password">Password</label><span className="password-field"><input id="password" type={show ? "text" : "password"} autoComplete={register ? "new-password" : "current-password"} value={password} onChange={(e) => setPassword(e.target.value)} required minLength={register ? 8 : undefined} disabled={pending} />
        <button type="button" className="password-toggle" aria-label={show ? "Hide password" : "Show password"} aria-pressed={show} onClick={() => setShow(!show)}>{show ? "Hide" : "Show"}</button></span></div>}
      {register && <p className="field-hint">Use at least 8 characters. Your account’s password policy also applies.</p>}
      <button className="button" disabled={pending}>{pending ? "Please wait…" : mode === "reset" ? "Send reset instructions" : register ? "Create account" : "Log in"}</button>
    </form>}
    {error && !(session.user && session.status === "error") && <p className="form-error" role="alert">{error}</p>}
    <nav className="auth-links" aria-label="Account">
      {mode !== "login" && <Link href={`/login${query}`}>Log in</Link>}
      {mode !== "register" && <Link href={`/register${query}`}>Create account</Link>}
      {mode !== "reset" && <Link href={`/forgot-password${query}`}>Forgot password</Link>}
    </nav>
  </section>;
}
