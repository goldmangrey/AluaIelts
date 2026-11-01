"use client";
import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { getReadingCatalog } from "../api";
import { readingApi } from "./api";
import { findOrStart } from "./start";
import { readingMessage } from "./messages";

const starts = new Map<string, Promise<string[]>>();
export function StartButton({ examId, uid, learnerId, hasAttempt }: { examId: string; uid: string; learnerId: string; hasAttempt: boolean }) {
  const router = useRouter(); const lock = useRef(false);
  const [busy, setBusy] = useState(false); const [error, setError] = useState<string | null>(null);
  const [choices, setChoices] = useState<string[]>([]);
  async function start() {
    if (lock.current) return;
    lock.current = true; setBusy(true); setError(null);
    const key = `alua:reading:start:${learnerId}:${examId}`;
    try {
      const run = () => findOrStart(examId, key, { catalog: () => getReadingCatalog(), storage: localStorage,
        create: (body) => readingApi(uid)("/reading/attempts", undefined, { method: "POST", body }),
      });
      let pending = starts.get(key);
      if (!pending) {
        pending = (async () => typeof navigator.locks?.request === "function" ? await navigator.locks.request(key, run) : await run())();
        starts.set(key, pending);
      }
      const ids = await pending;
      if (ids.length === 1) router.push(`/reading/attempts/${ids[0]}`);
      else setChoices(ids);
    } catch (failure) { setError(readingMessage(failure)); }
    finally { starts.delete(key); lock.current = false; setBusy(false); }
  }
  return <><button className="button" disabled={busy} onClick={() => void start()}>{busy ? "Opening test…" : hasAttempt ? "Continue test" : "Start test"}</button>
    {error && <p className="form-error" role="alert">{error} Retry uses the same start event.</p>}
    {choices.length > 0 && <div className="attempt-choices"><p>Choose an existing attempt to continue.</p>{choices.map((id, i) => <button className="text-button" key={id} onClick={() => router.push(`/reading/attempts/${id}`)}>Continue attempt {i + 1}</button>)}</div>}
  </>;
}
