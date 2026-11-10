/** Server-only contracts. Endpoints and model choices never come from public input. */
export type Provider = 'groq' | 'cloudflare' | 'gemini' | 'openrouter';
export interface AIEnv {
  GROQ_API_KEY?: string; GEMINI_API_KEY?: string; OPENROUTER_API_KEY?: string;
  AI_GEMINI_ENABLED?: string; AI_OPENROUTER_ENABLED?: string;
  /** Explicit operator approval, task names separated by commas. Empty denies external processing. */
  AI_EXTERNAL_TASKS?: string; AI_OPENROUTER_MODEL?: string;
  AI?: {run(model: string, input: Record<string, unknown>, options?: {signal?: AbortSignal}): Promise<unknown>};
}
export class ProviderError extends Error {
  constructor(public status: number, public retryable = false, public reason = 'provider_error', public retryAfterMs = 0) {
    super('AI provider request failed');
  }
}
export const transient = (s: number) => [408, 429, 500, 502, 503, 504].includes(s);
export interface AdapterInput {
  messages: {role: 'system' | 'user' | 'assistant'; content: string}[];
  temperature: number; maxTokens: number;
}
export type Adapter = (env: AIEnv, model: string, input: AdapterInput, signal: AbortSignal) => Promise<unknown>;
export function retryAfter(value: string | null, now = Date.now()): number {
  if (!value || value.length > 100) return 0;
  const ms = /^\d+(?:\.\d+)?$/.test(value) ? Number(value) * 1000 : Date.parse(value) - now;
  return Number.isFinite(ms) ? Math.min(300_000, Math.max(0, ms)) : 0;
}
export async function boundedJSON(response: Response, limit = 64_000): Promise<unknown> {
  const reader = response.body?.getReader();
  if (!reader) throw new ProviderError(502, true, 'empty_output');
  const decoder = new TextDecoder(); let text = '', size = 0;
  try {
    while (true) {
      const {done, value} = await reader.read(); if (done) break;
      size += value.byteLength; if (size > limit) throw new ProviderError(502, true, 'output_too_large');
      text += decoder.decode(value, {stream: true});
    }
    return JSON.parse(text + decoder.decode());
  } catch (error) {
    if (error instanceof ProviderError) throw error;
    throw new ProviderError(502, true, 'invalid_json');
  } finally { void reader.cancel().catch(() => {}); }
}
export async function requestJSON(url: string, init: RequestInit, fetcher: typeof fetch = fetch, limit?: number) {
  let response: Response;
  try {response = await fetcher(url, {...init, redirect: 'manual'});}
  catch (error) {
    if ((error as {name?: string})?.name === 'AbortError') throw new ProviderError(504, true, 'timeout');
    throw new ProviderError(503, true, 'network_error');
  }
  if (!response.ok) {
    void response.body?.cancel().catch(() => {});
    const s = response.status;
    throw new ProviderError(s, transient(s) || [401,403,404,410].includes(s),
      [401,403].includes(s) ? 'configuration_failure' : [404,410].includes(s) ? 'model_unavailable' : `http_${s}`,
      retryAfter(response.headers.get('retry-after')));
  }
  return boundedJSON(response, limit);
}
export function chatOutput(data: unknown) {
  const d = data as {choices?: {message?: {content?: unknown}}[]; response?: unknown};
  let content = d?.choices?.[0]?.message?.content ?? d?.response;
  if (Array.isArray(content) && content.every(p => p && (p.type === 'text' || p.type === 'output_text') && typeof p.text === 'string'))
    content = content.map(p => p.text).join('');
  if (typeof content === 'string' && content.trim() && content.length <= 12_000) return {response: content};
  if (content && typeof content === 'object' && !Array.isArray(content) && JSON.stringify(content).length <= 12_000) return {response: content};
  throw new ProviderError(502, true, 'empty_output');
}
export async function timed<T>(work: (signal: AbortSignal) => Promise<T>, ms: number): Promise<T> {
  const controller = new AbortController(); let timer: ReturnType<typeof setTimeout> | undefined;
  try {
    return await Promise.race([Promise.resolve().then(() => work(controller.signal)), new Promise<never>((_, reject) => {
      timer = setTimeout(() => { controller.abort(); reject(new ProviderError(504, true, 'timeout')); }, ms);
    })]);
  } finally { clearTimeout(timer); }
}
