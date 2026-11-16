'use client';

import Image from 'next/image';
import {useEffect, useRef, useState, type CSSProperties} from 'react';
import s from './lua-mascot.module.css';

type Emotion = 'thinking' | 'aha' | 'celebration' | 'support' | 'wink' | 'scholar' | 'listening' | 'sleepy' | 'wave' | 'proud' | 'happy' | 'puppy-eyes' | 'extra';
type Props = {mode?: 'idle' | 'static' | 'fallback'; emotion?: Emotion; size?: number; className?: string; context?: 'review' | 'detail' | 'continue'; priority?: boolean};

/** Decorative, fixed-size artwork. Learning state and requests belong to callers. */
export function LuaMascot({mode = 'static', emotion = 'support', size = 80, className = '', context, priority = false}: Props) {
  const root = useRef<HTMLSpanElement>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    const node = root.current;
    if (mode !== 'idle' || failed || !node) return;
    const motion = matchMedia('(prefers-reduced-motion: reduce)');
    let visible = false, disposed = false, timer: ReturnType<typeof setTimeout> | undefined;
    const images = Array.from(node.querySelectorAll('img[data-layer]'));
    let ready = false, hasBlinked = false;
    function clear() { clearTimeout(timer); node!.removeAttribute('data-lua-blink'); }
    function schedule() { timer = setTimeout(blink, hasBlinked ? 4000 + Math.random() * 3000 : 1000 + Math.random() * 1000); }
    function blink() {
      hasBlinked = true;
      node!.dataset.luaBlink = 'true';
      timer = setTimeout(() => {
        node!.removeAttribute('data-lua-blink');
        if (Math.random() < .18) timer = setTimeout(() => {
          node!.dataset.luaBlink = 'true';
          timer = setTimeout(() => { node!.removeAttribute('data-lua-blink'); schedule(); }, 145);
        }, 180);
        else schedule();
      }, 145);
    }
    function sync() {
      if (disposed) return;
      clear();
      node!.dataset.luaReady = String(ready);
      const active = ready && visible && !document.hidden && !motion.matches;
      node!.dataset.luaActive = String(active);
      if (active) schedule();
    }
    // Decode both heads before switching: no empty frame on the first blink.
    void Promise.all(images.map(img => (img as HTMLImageElement).decode())).then(() => { ready = true; sync(); }).catch(() => { if (!disposed) setFailed(true); });
    const observer = new IntersectionObserver(([entry]) => { visible = !!entry?.isIntersecting; sync(); });
    observer.observe(node);
    motion.addEventListener('change', sync);
    document.addEventListener('visibilitychange', sync);
    return () => { disposed = true; clear(); observer.disconnect(); motion.removeEventListener('change', sync); document.removeEventListener('visibilitychange', sync); };
  }, [mode, failed]);

  const image = (name: string, layer = false) => <Image src={`/images/lua/${name}.webp`} alt="" width={mode === 'static' && !failed ? 400 : 768} height={mode === 'static' && !failed ? 400 : 768} sizes={`${size}px`} unoptimized loading={priority || layer ? 'eager' : 'lazy'} fetchPriority={priority && name === 'composite' ? 'high' : 'auto'} data-layer={layer || undefined} onError={() => setFailed(true)}/>;
  return <span ref={root} className={`${s.mascot} ${mode === 'idle' && !failed ? s.idle : ''} ${className}`} style={{'--lua-size': `${size}px`} as CSSProperties} aria-hidden="true" data-lua-context={context}>
    {mode === 'idle' && !failed ? <>
      <span className={s.fallback}>{image('composite')}</span>
      <span className={s.layers}>
        <span className={s.breath}>
          <span className={s.tail}>{image('tail', true)}</span>
          <span className={s.body}>{image('body', true)}</span>
          <span className={s.head}><span className={s.open}>{image('head-open', true)}</span><span className={s.closed}>{image('head-closed', true)}</span></span>
        </span>
      </span>
    </> : image(mode === 'static' && !failed ? emotion : 'composite')}
  </span>;
}
