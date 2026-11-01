"use client";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { StatusPanel } from "@/components/status-panel";
import { logout, retrySession, useSession } from "./session";
import { authMessage } from "./messages";
export function ProfileView() {
  const session = useSession();
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const lock = useRef(false);
  useEffect(() => { if (session.status === "signed_out" && !lock.current) router.replace("/login?next=%2Fprofile"); }, [session.status, router]);
  async function perform(exit: boolean) {
    if (lock.current) return;
    lock.current = true; setBusy(true); setError(null);
    try { if (exit) { await logout(); router.replace("/"); router.refresh(); } else await retrySession(); }
    catch (failure) { setError(authMessage(failure)); }
    finally { lock.current = false; setBusy(false); }
  }
  return <section className="auth-shell"><p className="eyebrow">Your Alua account</p><h1>Your account.</h1>
    {session.status === "loading" && <p className="loading-text" role="status">Loading your account…</p>}
    {session.status === "error" && <StatusPanel title="Your account couldn’t load.">{authMessage(session.error)}</StatusPanel>}
    {session.status === "ready" && <dl className="profile-details">
      {session.user?.email && <div><dt>Email</dt><dd>{session.user.email}</dd></div>}
      {session.profile?.display_name && <div><dt>Name</dt><dd>{session.profile.display_name}</dd></div>}
    </dl>}
    {session.status === "error" && <button className="button secondary" disabled={busy} onClick={() => void perform(false)}>Retry account setup</button>}
    {(session.user || session.status === "error") && <button className="button secondary logout-button" disabled={busy} onClick={() => void perform(true)}>{busy ? "Please wait…" : "Log out"}</button>}
    {session.user&&<p className="small-note">Logging out removes local Reading drafts and highlights from this device. Save your answers first.</p>}
    {error && <p className="form-error" role="alert">{error}</p>}
  </section>;
}
