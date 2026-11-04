"use client";
import type { Auth, User } from "firebase/auth";
import { useSyncExternalStore } from "react";
import { getFirebaseAuth } from "@/lib/firebase/client";
import { withTimeout } from "@/lib/timeout";
import { ApiError } from "@/lib/api/client";
import { loadLearner, type LearnerProfile } from "./api";

interface Identity { uid: string; email: string | null }
export interface Session {
  status: "loading" | "signed_out" | "ready" | "error";
  user: Identity | null;
  profile: LearnerProfile | null;
  error?: unknown;
  generation: number;
}
const initial: Session = { status: "loading", user: null, profile: null, generation: 0 };
let state = initial;
const listeners = new Set<() => void>();
let started = false;
let observing = false;
let epoch = 0;
let action = false;
let job: { uid: string; promise: Promise<void> } | undefined;
function publish(next: Session) { state = next; listeners.forEach((listener) => listener()); }
function clear(status: Session["status"] = "signed_out", error?: unknown) {
  epoch++;
  job = undefined;
  publish({ status, user: null, profile: null, generation: epoch, error });
}
async function resolveUser(user: User, name?: string): Promise<void> {
  if (job?.uid === user.uid) return job.promise;
  const previous=state.user?.uid;
  const current = ++epoch;
  const identity = { uid: user.uid, email: user.email };
  publish({ status: "loading", user: identity, profile: null, generation: current });
  const promise = (async () => {
    try {
      const drafts=await import("@/features/reading/exam/draft-storage");
      if(previous && previous!==user.uid)await drafts.clearDraftOwner(previous);
      drafts.allowDraftOwner(user.uid);
      const profile = await loadLearner(name ?? user.displayName, user.uid);
      if (epoch === current) publish({ status: "ready", user: identity, profile, generation: current });
    } catch (error) {
      if (epoch === current) publish({ status: "error", user: error instanceof ApiError && error.status === 401 ? null : identity, profile: null, error, generation: current });
      throw error;
    } finally { if (epoch === current) job = undefined; }
  })();
  job = { uid: user.uid, promise };
  return promise;
}
async function observeFirebase(auth: Auth) {
  if (observing) return;
  const { onAuthStateChanged } = await import("firebase/auth");
  if (observing) return;
  observing = true;
  onAuthStateChanged(auth, (user) => {
    if (action) return;
    if (!user) {
      const previous=state.user?.uid;
      clear();
      if(previous)void import("@/features/reading/exam/draft-storage").then(m=>m.clearDraftOwner(previous)).catch(()=>{});
      return;
    }
    if (state.status === "ready" && state.user?.uid === user.uid) return;
    void resolveUser(user).catch(() => {}); // A terminal error is published by resolveUser.
  }, (error) => clear("error", error));
}
async function start() {
  if (started) return;
  started = true;
  try { await observeFirebase(await getFirebaseAuth()); }
  catch (error) { started = false; clear("error", error); }
}
function subscribe(listener: () => void) {
  listeners.add(listener);
  void start();
  return () => { listeners.delete(listener); };
}
export function useSession() { return useSyncExternalStore(subscribe, () => state, () => initial); }

export async function authenticate(mode: "login" | "register", email: string, password: string, name: string) {
  if (action) throw new ApiError(409, "auth_busy");
  action = true;
  try {
    const auth = await getFirebaseAuth();
    await observeFirebase(auth);
    const sdk = await import("firebase/auth");
    let user: User;
    if (mode === "register" && auth.currentUser) {
      // A partial signup is completed with the same Firebase identity, never create again.
      if (auth.currentUser.email?.toLowerCase() !== email.trim().toLowerCase()) {
        throw new ApiError(409, "different_account");
      }
      user = auth.currentUser;
    } else {
      const result = await withTimeout(mode === "register"
        ? sdk.createUserWithEmailAndPassword(auth, email.trim(), password)
        : sdk.signInWithEmailAndPassword(auth, email.trim(), password));
      user = result.user;
    }
    if (mode === "register" && name.trim()) {
      try { await withTimeout(sdk.updateProfile(user, { displayName: name.trim() })); }
      catch { /* Metadata outage must not repeat account creation; backend still receives name. */ }
    }
    job = undefined;
    await resolveUser(user, mode === "register" ? name : undefined);
  } finally { action = false; }
}
// Restored from the Nov 3 production build; prepare before the popup click.
export async function prepareGoogleAuth(mode: "sign-in" | "link" = "sign-in") {
  const [auth, sdk] = await Promise.all([getFirebaseAuth(), import("firebase/auth")]);
  await observeFirebase(auth);
  return async () => {
    if (action) throw new ApiError(409, "auth_busy");
    action = true;
    try {
      const provider = new sdk.GoogleAuthProvider();
      provider.setCustomParameters({ prompt: "select_account" });
      const current = auth.currentUser;
      if (mode === "link" && (!current || state.status !== "ready" || state.user?.uid !== current.uid)) throw new ApiError(401, "sign_in_required");
      const { user } = await (mode === "link" && current ? sdk.linkWithPopup(current, provider) : sdk.signInWithPopup(auth, provider));
      if (auth.currentUser?.uid !== user.uid) throw new ApiError(401, "session_changed");
      job = undefined;
      await resolveUser(user, user.displayName?.replace(/[\x00-\x1f]/g, "").trim().slice(0, 80));
      if (auth.currentUser?.uid !== user.uid || state.status !== "ready" || state.user?.uid !== user.uid) {
        const error = new ApiError(401, "session_changed"); clear("error", error); throw error;
      }
    } finally { action = false; }
  };
}
export async function retrySession() {
  const auth = await getFirebaseAuth();
  await observeFirebase(auth);
  if (!auth.currentUser) { clear(); return; }
  await resolveUser(auth.currentUser);
}
export async function logout() {
  if (action) throw new ApiError(409, "auth_busy");
  action = true;
  const previous=state.user?.uid;
  clear(); // Immediately unmount private UI and invalidate late profile/catalog responses.
  try {
    let cleanupError:unknown;
    if(previous)try{await (await import("@/features/reading/exam/draft-storage")).clearDraftOwner(previous)}catch(error){cleanupError=error}
    const auth = await getFirebaseAuth();
    const { signOut } = await import("firebase/auth");
    await withTimeout(signOut(auth));
    if(cleanupError)throw new ApiError(0,"draft_cleanup_failed");
  } catch (error) { clear("error", error); throw error; }
  finally { action = false; }
}

/** Invalidate the exact rejected session without clearing unrelated user state. */
export function rejectSession(generation: number) {
  if (state.generation === generation) clear("error", new ApiError(401, "session_expired"));
}
