"use client";
import type { Auth } from "firebase/auth";
import { ApiError } from "@/lib/api/client";
import { withTimeout } from "@/lib/timeout";

export function firebaseConfigured() {
  return !!(process.env.NEXT_PUBLIC_FIREBASE_API_KEY && process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN &&
    process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID && process.env.NEXT_PUBLIC_FIREBASE_APP_ID);
}
let initialization: Promise<Auth> | undefined;
export async function getFirebaseAuth(): Promise<Auth> {
  if (!firebaseConfigured()) throw new ApiError(0, "auth_not_configured");
  initialization ??= (async () => {
    const [{ getApps, initializeApp }, { getAuth, setPersistence, browserLocalPersistence }] = await Promise.all([
      import("firebase/app"), import("firebase/auth"),
    ]);
    const app = getApps().find((app) => app.name === "alua-web") ?? initializeApp({
      apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY,
      authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN,
      projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
      appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID,
      messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID,
    }, "alua-web");
    const auth = getAuth(app);
    const emulator = process.env.NEXT_PUBLIC_FIREBASE_AUTH_EMULATOR_URL;
    if (emulator) {
      // Unsigned emulator tokens must never reach a real Alua API/project.
      const address = new URL(emulator);
      const api = new URL(process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://invalid");
      if (process.env.NODE_ENV !== "development" || !app.options.projectId?.startsWith("demo-") ||
          !["localhost", "127.0.0.1"].includes(address.hostname) || address.protocol !== "http:" ||
          !["localhost", "127.0.0.1"].includes(api.hostname) || api.protocol !== "http:") {
        throw new ApiError(0, "auth_not_configured");
      }
      const { connectAuthEmulator } = await import("firebase/auth");
      if (!auth.emulatorConfig) connectAuthEmulator(auth, address.origin, { disableWarnings: true });
    }
    await setPersistence(auth, browserLocalPersistence);
    await auth.authStateReady();
    return auth;
  })().catch((error: unknown) => { initialization = undefined; throw error; });
  return withTimeout(initialization);
}
export async function getIdToken(forceRefresh = false, expectedUid?: string): Promise<string | null> {
  const auth = await getFirebaseAuth();
  const user = auth.currentUser;
  if (!user) return null;
  if (expectedUid && user.uid !== expectedUid) throw new ApiError(401, "session_changed");
  try {
    const token = await withTimeout(user.getIdToken(forceRefresh));
    if (auth.currentUser !== user) throw new ApiError(401, "session_changed");
    return token;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (error && typeof error === "object" && "code" in error && error.code === "auth/network-request-failed") throw new ApiError(0, "network_error");
    throw new ApiError(401, "session_expired");
  }
}
