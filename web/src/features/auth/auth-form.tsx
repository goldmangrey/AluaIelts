"use client";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { getFirebaseAuth } from "@/lib/firebase/client";
import { withTimeout } from "@/lib/timeout";
import { authenticate, logout, prepareGoogleAuth, retrySession, useSession } from "./session";
import { authMessage } from "./messages";
import { safeReturnPath } from "./redirect";

import s from "./login.module.css";
function GoogleIcon() { return <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path fill="#4285F4" d="M21.6 12.23c0-.71-.06-1.39-.18-2.05H12v3.88h5.38a4.6 4.6 0 0 1-2 3.02v2.51h3.24c1.9-1.75 2.98-4.33 2.98-7.36Z" /><path fill="#34A853" d="M12 22c2.7 0 4.96-.9 6.62-2.41l-3.24-2.51c-.9.6-2.05.96-3.38.96-2.6 0-4.8-1.76-5.59-4.12H3.07v2.59A10 10 0 0 0 12 22Z" /><path fill="#FBBC05" d="M6.41 13.92a6 6 0 0 1 0-3.84V7.49H3.07a10 10 0 0 0 0 9.02l3.34-2.59Z" /><path fill="#EA4335" d="M12 5.96c1.47 0 2.79.5 3.82 1.5l2.87-2.87A9.6 9.6 0 0 0 12 2a10 10 0 0 0-8.93 5.49l3.34 2.59A5.99 5.99 0 0 1 12 5.96Z" /></svg>; }
function AppleIcon() { return <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor" aria-hidden="true"><path d="M17.05 12.54c.03 3.02 2.65 4.03 2.68 4.04-.02.07-.42 1.44-1.38 2.85-.83 1.22-1.69 2.43-3.05 2.46-1.33.03-1.76-.8-3.28-.8-1.51 0-1.99.77-3.25.83-1.3.05-2.29-1.32-3.13-2.53-1.71-2.48-3.02-7.02-1.26-10.08a4.85 4.85 0 0 1 4.1-2.49c1.28-.02 2.49.88 3.27.88.78 0 2.25-1.09 3.79-.93.65.03 2.48.26 3.65 1.97-.1.06-2.18 1.27-2.14 3.8ZM14.55 5.13c.7-.85 1.17-2.04 1.04-3.22-1.01.04-2.23.67-2.96 1.52-.65.75-1.21 1.95-1.06 3.1 1.13.09 2.28-.57 2.98-1.4Z" /></svg>; }

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
  const login = mode === "login";
  const title = mode === "reset" ? "Reset password." : register ? "Create account." : "Welcome back.";
  const google = useRef<(() => Promise<void>) | null>(null);
  const googleLink = useRef<(() => Promise<void>) | null>(null);
  const [googleReady, setGoogleReady] = useState(false);
  const [linkAfterPassword, setLinkAfterPassword] = useState(false);
  useEffect(() => {
    if (!login) return;
    let live = true;
    Promise.all([prepareGoogleAuth(), prepareGoogleAuth("link")]).then(([signIn, link]) => {
      if (live) { google.current = signIn; googleLink.current = link; setGoogleReady(true); }
    }).catch(failure => { if (live) { google.current = googleLink.current = async () => { throw failure; }; setGoogleReady(true); } });
    return () => { live = false; };
  }, [login]);
  async function connectGoogle(link = false) {
    const run = link ? googleLink.current : google.current;
    if (locked.current || !run) return;
    locked.current = true; setBusy(true); setError(null);
    try { await run(); setPassword(""); router.replace(destination); router.refresh(); }
    catch (failure) { setError(authMessage(failure)); }
    finally { locked.current = false; setBusy(false); }
  }
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
        setPassword(""); if (!linkAfterPassword) { router.replace(destination); router.refresh(); }
      }
    } catch (failure) { setError(authMessage(failure)); }
    finally { locked.current = false; setBusy(false); }
  }
  async function recover() {
    if (locked.current) return;
    locked.current = true; setBusy(true); setError(null);
    try { await retrySession(); if (!linkAfterPassword) { router.replace(destination); router.refresh(); } }
    catch (failure) { setError(authMessage(failure)); }
    finally { locked.current = false; setBusy(false); }
  }
  const query = `?next=${encodeURIComponent(destination)}`;
  return <section className={login ? s.panel : "auth-shell"}>{!login && <p className="eyebrow">Your Alua account</p>}<h1>{title}</h1>
    <p className="subtitle">{mode === "reset" ? "We’ll help you get back to your account." : login ? "Sign in to continue your practice." : "Continue your IELTS practice."}</p>
    {mode !== "reset" && session.user ? <div className="auth-form">
      <p className="small-note">Signed in as {session.user.email ?? "your Alua account"}.</p>
      {session.status === "error" && <p role="alert" className="form-error">{authMessage(session.error)} Your sign-in is saved. Retry account setup without creating another account.</p>}
      {session.status === "loading" && <p role="status">Preparing your Alua profile…</p>}
      <button className="button" disabled={busy || session.status === "loading"} onClick={() => { if (session.status === "ready") router.replace(destination); else void recover(); }}>
        {busy ? "Please wait…" : session.status === "ready" ? "Continue" : "Retry account setup"}
      </button>
      {login && session.status === "ready" && <button type="button" className={s.social} disabled={busy || !googleReady} onClick={() => void connectGoogle(true)}><GoogleIcon />Connect Google to this account</button>}
      <button className="text-button" disabled={busy} onClick={async () => { try { await logout(); } catch (failure) { setError(authMessage(failure)); } }}>Use another account</button>
    </div> : sent ? <div className="auth-form" role="status"><h2>Check your inbox.</h2>
      <p className="small-note">If an account exists for this email, you’ll receive password reset instructions. Check your spam folder too.</p>
      <Link className="text-link" href={`/login${query}`}>Back to log in →</Link>
    </div> : <form className="auth-form" onSubmit={submit} aria-busy={busy}>
      {login && <><div className={s.socials}>
        <button type="button" className={s.social} disabled={pending || !googleReady || linkAfterPassword} onClick={() => void connectGoogle()}><GoogleIcon />Continue with Google</button>
        <button type="button" className={s.social} disabled aria-describedby="apple-soon"><AppleIcon /><span>Continue with Apple</span><small id="apple-soon">Coming soon</small></button>
      </div><p className={s.providerHint}>Have an Alua password? <button type="button" className={s.linkButton} aria-pressed={linkAfterPassword} disabled={pending} onClick={() => setLinkAfterPassword(!linkAfterPassword)}>Connect Google safely</button></p>
      {linkAfterPassword && <p className={s.notice} role="status">Log in with your password below. Then connect Google to the same account.</p>}
      <div className={s.divider}><span>or</span></div></>}
      {register && <label className="form-field">Name<input autoComplete="name" value={name} onChange={(e) => setName(e.target.value)} required maxLength={80} disabled={pending} /></label>}
      <label className="form-field">{login ? "Email address" : "Email"}<input placeholder={login ? "you@example.com" : undefined} type="email" autoComplete="email" autoCapitalize="none" spellCheck={false} value={email} onChange={(e) => setEmail(e.target.value)} required maxLength={254} disabled={pending} /></label>
      {mode !== "reset" && <div className="form-field"><div className={login ? s.passwordLabel : undefined}><label htmlFor="password">Password</label>{login && <Link href={`/forgot-password${query}`}>Forgot password?</Link>}</div><span className="password-field"><input id="password" type={show ? "text" : "password"} autoComplete={register ? "new-password" : "current-password"} value={password} onChange={(e) => setPassword(e.target.value)} required minLength={register ? 8 : undefined} disabled={pending} />
        <button type="button" className="password-toggle" aria-label={show ? "Hide password" : "Show password"} aria-pressed={show} onClick={() => setShow(!show)}>{show ? "Hide" : "Show"}</button></span></div>}
      {register && <p className="field-hint">Use at least 8 characters. Your account’s password policy also applies.</p>}
      <button className="button" disabled={pending}>{pending ? "Please wait…" : mode === "reset" ? "Send reset instructions" : register ? "Create account" : "Log in"}</button>
    </form>}
    {error && !(session.user && session.status === "error" && error === authMessage(session.error)) && <p className="form-error" role="alert">{error}</p>}
    {login ? <p className={s.registration}>New to Alua? <Link href={`/register${query}`}>Create account</Link></p> : <nav className="auth-links" aria-label="Account">
      <Link href={`/login${query}`}>Log in</Link>
      {mode !== "register" && <Link href={`/register${query}`}>Create account</Link>}
      {mode !== "reset" && <Link href={`/forgot-password${query}`}>Forgot password</Link>}
    </nav>}
  </section>;
}
