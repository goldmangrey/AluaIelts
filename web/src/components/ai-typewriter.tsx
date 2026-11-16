"use client";

import {useLayoutEffect, useRef, type ReactNode} from "react";
import s from "./ai-typewriter.module.css";

const storageKey = "alua:ai-reveal:v1";
const viewed = new Set<string>();
function hash(text: string) {
  let value = 2166136261;
  for (let i = 0; i < text.length; i++) value = Math.imul(value ^ text.charCodeAt(i), 16777619);
  return (value >>> 0).toString(36);
}
function hasViewed(key: string) {
  if (viewed.has(key)) return true;
  try { const saved: unknown = JSON.parse(sessionStorage.getItem(storageKey) ?? "[]"); return Array.isArray(saved) && saved.includes(key); }
  catch { return false; }
}
function remember(key: string) {
  viewed.add(key);
  if (viewed.size > 240) viewed.delete(viewed.values().next().value!);
  try {
    const saved: unknown = JSON.parse(sessionStorage.getItem(storageKey) ?? "[]");
    sessionStorage.setItem(storageKey, JSON.stringify([...new Set([...(Array.isArray(saved) ? saved.filter(v => typeof v === "string") : []), key])].slice(-240)));
  } catch { /* In-memory repeat-view protection also works when storage is unavailable. */ }
}

/** Presentation of a complete response. No network requests or per-character React state. */
export function AITypewriter({identity, content, active = true, children}: {
  identity: string; content: string; active?: boolean; children: ReactNode;
}) {
  const output = useRef<HTMLDivElement>(null), reserve = useRef<HTMLDivElement>(null);
  const finish = useRef<() => void>(() => {});
  const frameElement = useRef<HTMLDivElement>(null), skip = useRef<HTMLButtonElement>(null);
  const playback = useRef<{key:string;start:number;done:boolean}>(undefined);
  useLayoutEffect(() => {
    const root = output.current!, shadow = reserve.current!;
    const key = hash(identity) + ":" + hash(content);
    const motion = matchMedia("(prefers-reduced-motion: reduce)");
    const same = playback.current?.key === key;
    if (!active) { if (same) playback.current!.done = true; return; }
    if (motion.matches) { remember(key); return; }
    if (typeof Intl.Segmenter !== "function" || (same ? playback.current!.done : hasViewed(key))) return;
    if (!same) playback.current = {key,start:performance.now(),done:false};
    const blocks = [...root.querySelectorAll<HTMLElement>("p,blockquote")].filter(el => !el.closest("[data-ai-static]"));
    const copies = [...shadow.querySelectorAll<HTMLElement>("p,blockquote")].filter(el => !el.closest("[data-ai-static]"));
    const segmenter = new Intl.Segmenter(undefined, {granularity: "grapheme"});
    const nodes: {node: Text; text: string; parts: string[]; shown: number}[] = [];
    for (const block of blocks) {
      const walker = document.createTreeWalker(block, NodeFilter.SHOW_TEXT);
      while (walker.nextNode()) {
        const node = walker.currentNode as Text, text = node.data;
        if (text) nodes.push({node, text, parts: Array.from(segmenter.segment(text), part => part.segment), shown: -1});
      }
    }
    const total = nodes.reduce((sum, item) => sum + item.parts.length, 0);
    if (!total) return;
    const size = () => blocks.forEach((block, i) => { block.style.minHeight = `${copies[i]?.getBoundingClientRect().height ?? 0}px`; });
    size();
    const observer = new ResizeObserver(size); observer.observe(shadow);
    const cursor = document.createElement("span"); cursor.textContent = "▍";
    cursor.className = s.cursor!; cursor.setAttribute("aria-hidden", "true"); cursor.dataset.aiCursor = "true";
    nodes.forEach(item => { item.node.data = ""; });
    nodes[0]!.node.after(cursor);
    frameElement.current!.dataset.aiTyping = "true"; skip.current!.hidden = false;
    let frame = 0, stopped = false, last = 0;
    const start = playback.current!.start, speed = Math.max(75, total / 12);
    const complete = (finished = true) => {
      if (stopped) return; stopped = true;
      if(finished) { remember(key); if(playback.current?.key === key) playback.current.done = true; } cancelAnimationFrame(frame);
      nodes.forEach(item => { item.node.data = item.text; }); cursor.remove();
      observer.disconnect(); blocks.forEach(block => { block.style.minHeight = ""; });
      if(frameElement.current) frameElement.current.dataset.aiTyping = "false";
      if(skip.current) skip.current.hidden = true;
    };
    finish.current = complete;
    const tick = (now: number) => {
      if (stopped) return;
      if (!last) remember(key);
      if (now - last >= 40) {
        last = now; let remaining = Math.min(total, Math.floor((now - start) * speed / 1000));
        let placed = false;
        for (const item of nodes) {
          const count = Math.min(item.parts.length, remaining); remaining -= count;
          if (count !== item.shown) { item.node.data = item.parts.slice(0, count).join(""); item.shown = count; }
          if (!placed && count < item.parts.length) { item.node.after(cursor); placed = true; }
        }
        if (!placed) { complete(); return; }
      }
      frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    const reduce = () => { if (motion.matches) complete(); };
    motion.addEventListener("change", reduce);
    return () => { complete(false); motion.removeEventListener("change", reduce); finish.current = () => {}; };
  }, [identity, content, active]);
  return <div ref={frameElement} className={s.frame} data-ai-typing="false">
    <div className={s.control}><button ref={skip} hidden type="button" onClick={() => finish.current()}>Skip animation</button></div>
    <div className={s.layers}>
      <div className={s.reserve} ref={reserve} aria-hidden="true" inert>{children}</div>
      <div className={s.output} ref={output} aria-live="off">{children}</div>
    </div>
  </div>;
}
