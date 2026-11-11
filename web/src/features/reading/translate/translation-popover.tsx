"use client";
import { useEffect, useRef, useState, type RefObject } from "react";
import { createPortal } from "react-dom";
import { getIdToken } from "@/lib/firebase/client";
import { selectionContext, validateTranslation, type Translation } from "./context";
import styles from "./translation.module.css";

/** Exact UTF-16 range, including words split by existing manual highlights. */
function rangeFromOffsets(block: HTMLElement, start: number, end: number): Range | null {
  const text = block.textContent ?? "";
  if (start < 0 || end <= start || end > text.length) return null;
  const walker = block.ownerDocument.createTreeWalker(block, NodeFilter.SHOW_TEXT);
  const range = block.ownerDocument.createRange();
  let consumed = 0, started = false;
  for (let current = walker.nextNode(); current; current = walker.nextNode()) {
    const limit = consumed + (current.textContent?.length ?? 0);
    if (!started && start < limit) { range.setStart(current, start - consumed); started = true; }
    if (started && end <= limit) {
      range.setEnd(current, end - consumed);
      return range.toString() === text.slice(start, end) ? range : null;
    }
    consumed = limit;
  }
  return null;
}

/** Hit-test the actual word without modifying DOM markup or the user's selection. */
function wordAtPoint(root: HTMLElement, event: MouseEvent) {
  if (!(event.target instanceof Element) || event.target.closest("button,a,input,textarea,select,[contenteditable]")) return null;
  const block = event.target.closest<HTMLElement>("[data-highlight-block]");
  if (!block || !root.contains(block)) return null;
  const doc = root.ownerDocument as Document & {
    caretPositionFromPoint?: (x: number, y: number) => { offsetNode: Node; offset: number } | null;
    caretRangeFromPoint?: (x: number, y: number) => Range | null;
  };
  const position = doc.caretPositionFromPoint?.(event.clientX, event.clientY);
  const caret = position ? null : doc.caretRangeFromPoint?.(event.clientX, event.clientY);
  const node = position?.offsetNode ?? caret?.startContainer;
  const offset = position?.offset ?? caret?.startOffset;
  if (!node || offset === undefined || node.nodeType !== Node.TEXT_NODE || !block.contains(node)) return null;
  const before = doc.createRange(); before.selectNodeContents(block); before.setEnd(node, offset);
  const at = before.toString().length, text = block.textContent ?? "";
  const word = [...text.matchAll(/[A-Za-z]+(?:['’\-][A-Za-z]+)*/g)].find(match => match.index <= at && at <= match.index + match[0].length);
  if (!word) return null;
  const input = selectionContext(text, word.index, word.index + word[0].length);
  if (!input) return null;
  const range = rangeFromOffsets(block, word.index, word.index + word[0].length);
  if (!range) return null;
  // Caret APIs snap nearby blank space to text; require a real hit on a glyph box.
  const rect = [...range.getClientRects()].find(rect => event.clientX >= rect.left && event.clientX <= rect.right && event.clientY >= rect.top && event.clientY <= rect.bottom);
  return rect ? { block, input, rect, sentenceStart: word.index - input.start } : null;
}

export function TranslationPopover({ root, uid, attemptId, passageId, highlightExpression = false }: {
  root: RefObject<HTMLElement | null>; uid: string; attemptId: string; passageId: string; highlightExpression?: boolean;
}) {
  const card = useRef<HTMLDivElement>(null);
  const [enabled, setEnabled] = useState(false);
  const dismiss = useRef<() => void>(() => {});
  const cache = useRef(new Map<string, Translation>());
  const [state, setState] = useState<{ x: number; y: number; loading: boolean; result?: Translation; error?: string } | null>(null);
  useEffect(() => {
    const passage = root.current;
    if (!enabled || !passage) return;
    let pending: AbortController | undefined;
    let last = "", revision = 0;
    let pointer: { x: number; y: number } | undefined;
    const clearHighlight = () => {
      if (highlightExpression && typeof CSS !== "undefined" && "highlights" in CSS) CSS.highlights.delete("alua-translation");
    };
    const showHighlight = (hit: NonNullable<ReturnType<typeof wordAtPoint>>, result: Translation) => {
      if (!highlightExpression || typeof CSS === "undefined" || !("highlights" in CSS) || typeof Highlight === "undefined") return;
      const { input, block, sentenceStart } = hit;
      for (let from = 0; from <= input.start;) {
        const index = input.sentence.indexOf(result.expression, from);
        if (index < 0) return;
        const end = index + result.expression.length;
        if (index <= input.start && end >= input.end &&
            !/[A-Za-z'’\-]/.test(input.sentence[index - 1] ?? "") && !/[A-Za-z'’\-]/.test(input.sentence[end] ?? "")) {
          const range = rangeFromOffsets(block, sentenceStart + index, sentenceStart + end);
          if (range?.toString() === result.expression) CSS.highlights.set("alua-translation", new Highlight(range));
          return;
        }
        from = index + 1;
      }
    };
    const close = () => { clearHighlight(); pending?.abort(); revision++; last = ""; setState(null); };
    dismiss.current = close;
    async function translate(event: MouseEvent) {
      if (event.button !== 0 || event.detail > 1 || pointer && Math.hypot(event.clientX - pointer.x, event.clientY - pointer.y) > 8) return;
      const hit = wordAtPoint(passage!, event);
      if (!hit) return;
      // Translating a highlighted word must not remove its highlight.
      event.stopPropagation();
      const { block, input, rect } = hit;
      const key = JSON.stringify([uid, attemptId, passageId, block.dataset.highlightBlock, input]);
      if (key === last) return;
      close(); last = key;
      if (!rect.width || !rect.height) return;
      const x = Math.max(12, Math.min(rect.left, window.innerWidth - 292));
      const y = rect.bottom + 10 + 142 < window.innerHeight ? rect.bottom + 10 : Math.max(12, rect.top - 142);
      const cached = cache.current.get(key);
      if (cached) { showHighlight(hit, cached); setState({ x, y, loading: false, result: cached }); return; }
      setState({ x, y, loading: true });
      const controller = new AbortController(); pending = controller;
      const current = revision;
      const timeout = setTimeout(() => controller.abort(), 20_000);
      let errorMessage = "Перевод временно недоступен. Попробуйте позже.";
      try {
        const token = await getIdToken(false, uid);
        controller.signal.throwIfAborted();
        if (!token) { errorMessage = "Войдите в аккаунт для перевода."; throw Error(); }
        const response = await fetch("/api/translate", {
          method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
          body: JSON.stringify({ ...input, attemptId, passageId, block: Number(block.dataset.highlightBlock) }),
          signal: controller.signal, cache: "no-store", credentials: "omit",
        });
        let payload: unknown;
        try { payload = await response.json(); } catch { payload = null; }
        if (!response.ok) {
          if (process.env.NODE_ENV === "development") {
            const error = payload && typeof payload === "object" && "error" in payload ? payload.error : null;
            const code = error && typeof error === "object" && "code" in error && typeof error.code === "string" && /^[a-z_]{1,80}$/.test(error.code) ? error.code : "unexpected_response";
            console.warn("[smart-translate]", { status: response.status, code });
          }
          errorMessage = response.status === 429 ? (payload&&typeof payload==='object'&&'error' in payload&&(payload.error as {code?:string})?.code==='translate_busy'?"Предыдущий перевод ещё готовится. Повторите через секунду.":"Слишком много запросов. Подождите минуту.") :
            response.status === 401 ? "Войдите в аккаунт для перевода." :
            response.status === 403 ? "Перевод недоступен для этой попытки." :
            [400, 422].includes(response.status) ? "Не удалось определить слово. Нажмите на него ещё раз." :
            response.status === 504 ? "Перевод занял слишком много времени. Попробуйте ещё раз." :
            response.status === 502 ? "Не удалось получить точный перевод. Нажмите на слово ещё раз." : errorMessage;
          throw Error();
        }
        const result = validateTranslation(payload, input);
        if (!result) {
          errorMessage = "Не удалось получить точный перевод. Нажмите на слово ещё раз.";
          if (process.env.NODE_ENV === "development") console.warn("[smart-translate]", { status: 200, code: "invalid_translation" });
          throw Error();
        }
        if (current !== revision) return;
        if (cache.current.size >= 100) cache.current.delete(cache.current.keys().next().value!);
        cache.current.set(key, result); showHighlight(hit, result); setState({ x, y, loading: false, result });
      } catch {
        if (current === revision) {
          last = "";
          setState({ x, y, loading: false, error: controller.signal.aborted ? "Перевод занял слишком много времени. Попробуйте ещё раз." : errorMessage });
        }
      } finally { clearTimeout(timeout); }
    }
    const down = (event: PointerEvent) => { pointer = { x: event.clientX, y: event.clientY }; };
    const outside = (event: PointerEvent) => {
      if (!passage.contains(event.target as Node) && !card.current?.contains(event.target as Node)) close();
    };
    const key = (event: KeyboardEvent) => { if (event.key === "Escape") close(); };
    const scroll = (event: Event) => { if (!card.current?.contains(event.target as Node)) close(); };
    const click = (event: MouseEvent) => { void translate(event); };
    passage.addEventListener("pointerdown", down, { passive: true });
    passage.addEventListener("click", click, true);
    // Global listeners only dismiss the card; word detection stays on Passage.
    document.addEventListener("pointerdown", outside, { passive: true });
    document.addEventListener("keydown", key);
    document.addEventListener("scroll", scroll, true);
    window.addEventListener("resize", close);
    return () => {
      clearHighlight(); pending?.abort(); revision++;
      dismiss.current = () => {};
      passage.removeEventListener("pointerdown", down);
      passage.removeEventListener("click", click, true);
      document.removeEventListener("pointerdown", outside);
      document.removeEventListener("keydown", key);
      document.removeEventListener("scroll", scroll, true);
      window.removeEventListener("resize", close);
    };
  }, [root, uid, attemptId, passageId, enabled, highlightExpression]);
  return <><button type="button" className={styles.toggle} aria-pressed={enabled} onClick={() => {
    dismiss.current(); setState(null); setEnabled(value => !value);
  }}><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M4 5h12M10 3v2M6 5c0 6 5 10 8 11M14 5c0 5-4 10-10 13M14 21l4-10 4 10M15.5 17h5" /></svg>Translate</button>{enabled && state && createPortal(<div ref={card} className={styles.card} style={{ left: state.x, top: state.y }} role="status" aria-live="polite" aria-label="Перевод" lang="ru">
    <button type="button" className={styles.close} aria-label="Закрыть перевод" onClick={() => dismiss.current()}>×</button>
    {state.loading ? <span className={styles.loading}><span className={styles.dot} />Переводим…</span> : state.result ? <><strong lang="en">{state.result.expression}</strong><span>{state.result.translation}</span></> : <span className={styles.error}>{state.error}</span>}
  </div>, document.body)}</>;
}
