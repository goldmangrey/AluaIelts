"use client";
import { createContext, useContext, useEffect, useState } from "react";
import type { Asset } from "./models";
import { readingApi } from "./api";
export const AssetLoaderContext = createContext<((id: string, signal: AbortSignal) => Promise<Blob>) | null>(null);
export function AssetImage({ asset, uid, active, alt }: { asset: Asset; uid: string; active: boolean; alt: string }) {
  const loadAsset = useContext(AssetLoaderContext);
  const [state, setState] = useState<{ url?: string; error?: boolean }>({});
  const [revision, retry] = useState(0);
  useEffect(() => {
    if (!active) return;
    const controller = new AbortController(); let url: string | undefined;
    const request = loadAsset ? loadAsset(asset.id, controller.signal) : readingApi(uid)(`/reading/assets/${encodeURIComponent(asset.id)}`, controller.signal, undefined, "blob");
    request.then((blob) => {
      if (!(blob instanceof Blob) || blob.type !== "image/png") throw new Error("Invalid image");
      if (controller.signal.aborted) return;
      url = URL.createObjectURL(blob); setState({ url });
    }).catch(() => { if (!controller.signal.aborted) setState({ error: true }); });
    return () => { controller.abort(); if (url) URL.revokeObjectURL(url); };
  }, [asset.id, uid, revision, active, loadAsset]);
  return <div className="reading-asset" style={{ aspectRatio: `${asset.width}/${asset.height}` }}>
    {state.error ? <div role="alert">Task image couldn’t load.<button type="button" className="text-button" onClick={() => { setState({}); retry((n) => n + 1); }}>Retry image</button></div> : state.url ?
      // Blob URL is fetched with Bearer auth; next/image would not forward it.
      // eslint-disable-next-line @next/next/no-img-element
      <img src={state.url} alt={alt} width={asset.width} height={asset.height} onError={() => setState({ error: true })} /> : <p role="status">Loading task image…</p>}
  </div>;
}
