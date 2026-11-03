"use client";
import { memo, useCallback, useEffect, useRef, useState } from "react";
import type { Passage } from "./models";
import type { Highlight } from "./draft-storage";
import { eventId } from "./api";
import { TranslationPopover } from "../translate/translation-popover";
import translateStyles from "../translate/translation.module.css";
import styles from "./passage.module.css";

type Comfort = { uid: string; attemptId: string; onSizeChange: (size: number) => void };
function Icon({ name }: { name: "focus" | "highlight" | "bookmark" | "clear" }) {
  return <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{name === "bookmark" ? <path d="M6 4h12v17l-6-4-6 4V4Z" /> : name === "focus" ? <><path d="M8 3H3v5m13-5h5v5M3 16v5h5m13-5v5h-5M8 12h8" /></> : name === "clear" ? <path d="m14 3 7 7-11 11H6l-4-4L14 3Zm-8 10 7 7m-3 1h12" /> : <><path d="m15 3 6 6-10 10-6-6L15 3ZM5 13l-2 8 8-2M14 4l6 6" /></>}</svg>;
}
export const PassagePane = memo(function PassagePane({ passage, size, highlights = [], onHighlights, translation, comfort }: {
  passage: Passage; size: number; highlights?: Highlight[]; onHighlights?: (value: Highlight[]) => void;
  translation?: { uid: string; attemptId: string }; comfort?: Comfort;
}) {
  const article = useRef<HTMLElement>(null);
  const [selection, setSelection] = useState<{ passageId: string; block: number; start: number; end: number; quote: string } | null>(null);
  const [focus, setFocus] = useState(false);
  const [focused, setFocused] = useState<string | null>(null);
  const bookmarkKey = comfort ? `alua:reading:bookmarks:v2:${comfort.uid}:${comfort.attemptId}:${passage.id}` : "";
  const [bookmarks, setBookmarks] = useState<{ key: string; blocks: number[] }>({ key: "", blocks: [] });
  const marked = bookmarks.key === bookmarkKey ? bookmarks.blocks : [];
  const lastBookmark = useRef(-1);
  useEffect(() => {
    if (!bookmarkKey) return;
    let active = true;
    queueMicrotask(() => {
      let blocks: number[] = [];
      try {
        const stored: unknown = JSON.parse(localStorage.getItem(bookmarkKey) ?? "[]");
        if (Array.isArray(stored)) blocks = [...new Set(stored.filter((index): index is number => Number.isInteger(index) && passage.content[index]?.type === "paragraph"))];
      } catch { /* Local preferences are optional. */ }
      if (active) setBookmarks({ key: bookmarkKey, blocks });
    });
    return () => { active = false; };
  }, [bookmarkKey, passage.content]);
  const select = useCallback(() => {
    if (!onHighlights) return;
    const s = window.getSelection();
    if (!s || s.isCollapsed || s.rangeCount !== 1) { setSelection(null); return; }
    const range = s.getRangeAt(0), element = range.startContainer.parentElement?.closest<HTMLElement>("[data-highlight-block]");
    if (!element || !article.current?.contains(element) || !element.contains(range.endContainer)) { setSelection(null); return; }
    const before = range.cloneRange(); before.selectNodeContents(element); before.setEnd(range.startContainer, range.startOffset);
    const block = Number(element.dataset.highlightBlock), start = before.toString().length, quote = range.toString(), end = start + quote.length;
    if (quote.length > 10000 || !quote.trim() || passage.content[block]?.text.slice(start, end) !== quote) { setSelection(null); return; }
    setSelection({ passageId: passage.id, block, start, end, quote });
  }, [onHighlights, passage.content, passage.id]);
  useEffect(() => {
    if (!comfort || !onHighlights) return;
    document.addEventListener("selectionchange", select);
    return () => document.removeEventListener("selectionchange", select);
  }, [comfort, onHighlights, select]);
  function highlight() {
    if (!selection || selection.passageId !== passage.id || !onHighlights) return;
    const value = { id: eventId(), ...selection };
    onHighlights([...highlights.filter(h => h.passageId !== passage.id || h.block !== value.block || h.end <= value.start || h.start >= value.end), value].slice(-300));
    window.getSelection()?.removeAllRanges(); setSelection(null);
  }
  function toggleBookmark(block: number) {
    const blocks = marked.includes(block) ? marked.filter(index => index !== block) : [...marked, block].sort((a, b) => a - b);
    setBookmarks({ key: bookmarkKey, blocks });
    try { localStorage.setItem(bookmarkKey, JSON.stringify(blocks)); } catch { /* Keep available in memory. */ }
  }
  function jumpToBookmark() {
    const next = marked.find(index => index > lastBookmark.current) ?? marked[0];
    if (next === undefined) return;
    lastBookmark.current = next;
    const paragraph = article.current?.querySelector<HTMLElement>(`[data-paragraph="${next}"]`);
    paragraph?.scrollIntoView({ block: "center", behavior: "auto" });
    paragraph?.focus({ preventScroll: true });
  }
  function content(text: string, index: number) {
    const ranges = highlights.filter(h => h.passageId === passage.id && h.block === index && text.slice(h.start, h.end) === h.quote).sort((a, b) => a.start - b.start);
    let offset = 0; const parts = [];
    for (const h of ranges) {
      if (h.start < offset) continue;
      parts.push(text.slice(offset, h.start));
      parts.push(<mark key={h.id} title="Click to remove highlight" onClick={() => onHighlights?.(highlights.filter(v => v.id !== h.id))}>{text.slice(h.start, h.end)}</mark>); offset = h.end;
    }
    parts.push(text.slice(offset)); return parts;
  }
  const hasHighlights = highlights.some(h => h.passageId === passage.id);
  const translate = translation && <TranslationPopover key={`${translation.uid}:${passage.id}`} root={article} uid={translation.uid} attemptId={translation.attemptId} passageId={passage.id} highlightExpression={!!comfort} />;
  return <article ref={article} className={`passage-article${comfort ? ` ${styles.comfort}` : ""}`} style={{ fontSize: size }} onMouseUp={select} onKeyUp={select} onClick={event => {
    if (!comfort || !focus || !(event.target instanceof Element) || event.target.closest("button,a,input,textarea,select,mark,[contenteditable]")) return;
    if (!window.getSelection()?.isCollapsed) return;
    const paragraph = event.target.closest<HTMLElement>("[data-paragraph]");
    if (paragraph) setFocused(`${passage.id}:${paragraph.dataset.paragraph}`);
  }}>
    {comfort && <div className={styles.toolbar} role="toolbar" aria-label="Reading tools">
      <div className={styles.sizes} role="group" aria-label="Passage text size"><span aria-hidden="true">Aa</span>{[16, 18, 20].map(value => <button key={value} type="button" aria-label={`${value}px · ${value === 16 ? "Compact" : value === 18 ? "Comfortable" : "Large"}`} aria-pressed={size === value} onClick={() => comfort.onSizeChange(value)}>{value}</button>)}</div>
      <button type="button" aria-pressed={focus} onClick={() => setFocus(value => !value)}><Icon name="focus" />Focus</button>
      {onHighlights && <button type="button" disabled={!selection || selection.passageId !== passage.id} title="Select text, then highlight" onMouseDown={event => event.preventDefault()} onClick={highlight}><Icon name="highlight" />Highlight</button>}
      {translate}
      <button type="button" aria-label={marked.length ? `Go to bookmarked paragraph (${marked.length})` : "No bookmarked paragraphs"} title="Go to next bookmarked paragraph" disabled={!marked.length} onClick={jumpToBookmark}><Icon name="bookmark" />{marked.length > 0 && <span>{marked.length}</span>}</button>
      {onHighlights && hasHighlights && <button type="button" aria-label="Clear passage highlights" title="Clear passage highlights" onClick={() => onHighlights(highlights.filter(h => h.passageId !== passage.id))}><Icon name="clear" /></button>}
    </div>}
    <div className={translateStyles.header}><p className="eyebrow">Reading passage {passage.number}</p>{!comfort && translate}</div>
    <h1>{comfort && (!passage.title.trim() || passage.title.trim().toLowerCase() === "untitled") ? `Reading Passage ${passage.number}` : passage.title}</h1>
    {passage.subtitle && <p className="passage-subtitle">{passage.subtitle}</p>}
    {!comfort && onHighlights && <div className="highlight-actions">{selection?.passageId === passage.id && <button type="button" onMouseDown={event => event.preventDefault()} onClick={highlight}>Highlight</button>}{hasHighlights && <button type="button" onClick={() => onHighlights(highlights.filter(h => h.passageId !== passage.id))}>Clear passage highlights</button>}</div>}
    {passage.content.map((b, i) => b.type === "heading" ? b.text.trim() === passage.title.trim() ? null : <h2 key={i}>{b.text}</h2> : <p key={i} data-paragraph={comfort ? i : undefined} tabIndex={comfort ? -1 : undefined} className={comfort ? `${styles.paragraph}${focus && focused === `${passage.id}:${i}` ? ` ${styles.focused}` : ""}` : undefined}>
      {comfort && <button type="button" className={styles.bookmark} aria-label={`Bookmark paragraph ${b.label || i + 1}`} aria-pressed={marked.includes(i)} onClick={() => toggleBookmark(i)}><Icon name="bookmark" /></button>}
      {b.label && <strong className="paragraph-label">{b.label} </strong>}<span data-highlight-block={i} onClick={comfort ? select : undefined}>{content(b.text, i)}</span>
    </p>)}
  </article>;
});
