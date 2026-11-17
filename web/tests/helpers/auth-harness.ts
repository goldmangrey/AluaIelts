import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { resolve } from "node:path";
import ts from "typescript";
import type { ReactElement, ReactNode } from "react";
import { ApiError } from "../../src/lib/api/client";
import { resolveLearner } from "../../src/features/auth/api";
import { safeReturnPath } from "../../src/features/auth/redirect";
import { authMessage } from "../../src/features/auth/messages";
import { withTimeout } from "../../src/lib/timeout";
import type { Session } from "../../src/features/auth/session";

// Execute the real modules with isolated Firebase/React bindings; no SDK credentials or network.
function source<T>(file: string, bindings: Record<string, unknown>): T {
  const code = ts.transpileModule(readFileSync(resolve(file), "utf8"), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX },
  }).outputText;
  const exports = {};
  const require = createRequire(resolve("package.json"));
  new Function("require", "exports", code)((name: string) => {
    if (name in bindings) return bindings[name];
    if (name === "react/jsx-runtime") return require(name);
    throw new Error(`Unexpected test dependency: ${name}`);
  }, exports);
  return exports as T;
}

export function sessionHarness(request: Parameters<typeof resolveLearner>[0], restoredUid = "restored") {
  type User = { uid: string; email: string; displayName: string };
  const user = (uid: string): User => ({ uid, email: `${uid}@example.test`, displayName: uid });
  const auth: { currentUser: User | null } = { currentUser: user(restoredUid) };
  let observer: ((u: User | null) => void) | undefined;
  let subscribed = false;
  const states: Session[] = [];
  const signals: AbortSignal[] = [];
  const sdk = {
    onAuthStateChanged: (_auth: unknown, callback: typeof observer) => {
      observer = callback;
      callback?.(auth.currentUser);
    },
    signOut: async () => { auth.currentUser = null; observer?.(null); },
  };
  const session = source<typeof import("../../src/features/auth/session")>("src/features/auth/session.ts", {
    react: { useSyncExternalStore: (subscribe: (callback: () => void) => void, snapshot: () => Session) => {
      if (!subscribed) { subscribed = true; subscribe(() => { states.push(snapshot()); }); }
      return snapshot();
    } },
    "@/lib/firebase/client": { getFirebaseAuth: async () => auth },
    "firebase/auth": sdk,
    "./redirect": { safeReturnPath },
    "@/lib/timeout": { withTimeout },
    "@/lib/api/client": { ApiError },
    "./api": { loadLearner: (name: string, uid: string, options: Parameters<typeof resolveLearner>[3]) => {
      if (options?.signal) signals.push(options.signal);
      return resolveLearner(request, name, uid, options);
    } },
    "@/features/reading/exam/draft-storage": { allowDraftOwner: () => {}, clearDraftOwner: async () => {} },
  });
  session.useSession();
  return {
    session, states, signals, auth,
    snapshot: () => session.useSession(),
    switchUser: (uid: string) => { auth.currentUser = user(uid); observer?.(auth.currentUser); },
  };
}

// Minimal deterministic hook runner: effects execute after a render, state/refs survive rerenders.
// Tests exercise actual AuthForm effects and handlers rather than a copied redirect predicate.
export function formHarness(snapshot: () => Session, next: string, authenticate: () => Promise<void> = async () => {}) {
  const slots: unknown[] = [];
  const dependencies = new Map<number, readonly unknown[] | undefined>();
  let cursor = 0;
  let effects: (() => void)[] = [];
  const redirects: string[] = [];
  const router = { replace: (path: string) => { redirects.push(path); }, refresh: () => {} };
  const react = {
    useState: (initial: unknown) => {
      const index = cursor++;
      if (!(index in slots)) slots[index] = initial;
      return [slots[index], (value: unknown) => { slots[index] = value; }];
    },
    useRef: (initial: unknown) => {
      const index = cursor++;
      if (!(index in slots)) slots[index] = { current: initial };
      return slots[index];
    },
    useEffect: (effect: () => void, deps?: readonly unknown[]) => {
      const index = cursor++;
      const previous = dependencies.get(index);
      if (!deps || !previous || deps.some((value, i) => value !== previous[i])) effects.push(effect);
      dependencies.set(index, deps);
    },
  };
  const { AuthForm } = source<typeof import("../../src/features/auth/auth-form")>("src/features/auth/auth-form.tsx", {
    react,
    "next/link": { default: "a" },
    "next/navigation": { useRouter: () => router, useSearchParams: () => new URLSearchParams({ next }) },
    "@/lib/firebase/client": { getFirebaseAuth: async () => ({}) },
    "@/lib/timeout": { withTimeout },
    "./session": { useSession: snapshot, authenticate, logout: async () => {}, retrySession: async () => {}, prepareGoogleAuth: async () => async () => {} },
    "./messages": { authMessage }, "./redirect": { safeReturnPath }, "./login.module.css": { default: {} },
  });
  return {
    redirects,
    render: () => {
      cursor = 0; effects = [];
      const tree = AuthForm({ mode: "login" });
      effects.forEach(effect => effect());
      return tree;
    },
  };
}

export function elements(tree: ReactNode): ReactElement<Record<string, unknown>>[] {
  if (Array.isArray(tree)) return tree.flatMap(elements);
  if (!tree || typeof tree !== "object" || !("props" in tree)) return [];
  const node = tree as ReactElement<{ children?: ReactNode }>;
  return [node as ReactElement<Record<string, unknown>>, ...elements(node.props.children)];
}
