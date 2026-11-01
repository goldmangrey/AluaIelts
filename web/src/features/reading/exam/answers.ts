import type { Attempt } from "./models";
import { eventId } from "./api";
import { ApiError } from "@/lib/api/client";
export interface SaveEvent { event_id: string; expected_version: number; answers: Record<string, string> }
export type SaveAnswers = (event: SaveEvent) => Promise<Attempt>;
interface Snapshot { answers: Record<string, string>; dirty: number; saving: boolean; error: unknown; terminal: boolean }
/** One in-flight CAS write; explicit retry replays the exact UUID and payload. No offline queue. */
export class AnswerSession {
  private version: number; private saved: Record<string, string>; private timer?: ReturnType<typeof setTimeout>;
  private listeners = new Set<() => void>(); private pending?: SaveEvent; private flight?: Promise<void>; private disposed = false;
  private state: Snapshot;
  constructor(private attempt: Attempt, private send: SaveAnswers) {
    this.version = attempt.version; this.saved = { ...attempt.answers };
    this.state = { answers: { ...attempt.answers }, dirty: 0, saving: false, error: null, terminal: attempt.status !== "in_progress" };
  }
  snapshot = () => this.state;
  subscribe = (listener: () => void) => { this.listeners.add(listener); return () => { this.listeners.delete(listener); }; };
  private publish(change: Partial<Snapshot>) {
    if (this.disposed) return;
    this.state = { ...this.state, ...change };
    this.state.dirty = Object.keys(this.state.answers).filter((id) => (this.state.answers[id] ?? "") !== (this.saved[id] ?? "")).length;
    this.listeners.forEach((fn) => fn());
  }
  change = (changes: Record<string, string>) => {
    if (this.state.terminal || this.disposed || this.state.error instanceof ApiError && this.state.error.status === 409) return;
    this.publish({ answers: { ...this.state.answers, ...changes } });
    clearTimeout(this.timer);
    if (!this.state.error) this.timer = setTimeout(() => void this.flush(), 600);
  };
  flush = async (): Promise<void> => {
    clearTimeout(this.timer);
    if (this.flight) { await this.flight; if (!this.state.error && this.state.dirty) return this.flush(); return; }
    if (this.disposed || this.state.terminal || (!this.state.dirty && !this.pending)) return;
    const changes = Object.fromEntries(Object.entries(this.state.answers).filter(([id, answer]) => answer !== (this.saved[id] ?? "")));
    this.pending ??= { event_id: eventId(), expected_version: this.version, answers: changes };
    const event = this.pending;
    this.publish({ saving: true, error: null });
    this.flight = (async () => {
      try {
        const ack = await this.send(event);
        if (ack.id !== this.attempt.id || ack.exam_id !== this.attempt.exam_id || ack.mutation_applied !== true || ack.version !== event.expected_version + 1) throw new ApiError(409, "reading_attempt_completed");
        if (ack.status !== "in_progress") { this.publish({ terminal: true }); throw new ApiError(409, "reading_attempt_completed"); }
        this.version = ack.version;
        this.saved = { ...this.saved, ...event.answers };
        this.pending = undefined;
        this.publish({ saving: false });
      } catch (error) { this.publish({ saving: false, error }); }
      finally { this.flight = undefined; }
    })();
    await this.flight;
    if (!this.state.error && this.state.dirty && !this.disposed) return this.flush();
  };
  private mounts = 0;
  mount() { this.mounts++; }
  unmount() { this.mounts--; queueMicrotask(() => { if (this.mounts === 0) this.dispose(); }); }
  dispose() { this.disposed = true; clearTimeout(this.timer); this.listeners.clear(); }
}
