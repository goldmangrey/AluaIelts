/** Compatibility facade for the existing AI layer. All task routing lives in orchestrator.ts. */
import {ai} from './orchestrator';
import {groqAdapter} from './adapters/groq';
import {cloudflareAdapter} from './adapters/cloudflare';
import {type AIEnv, type AdapterInput, ProviderError, timed} from './adapters/common';
import {models} from './tasks';
export {ProviderError};
export type {AIEnv};
function input(value: Record<string, unknown>): AdapterInput {
  return {messages: (value.messages ?? []) as AdapterInput['messages'], temperature: Number(value.temperature) || 0,
    maxTokens: Math.min(1800, Math.max(1, Number(value.max_completion_tokens ?? value.max_tokens) || 1600))};
}
export async function groq(env: AIEnv, value: Record<string, unknown>, ms = 18_000, fetcher: typeof fetch = fetch) {
  return timed(signal => groqAdapter(env, models.groq, input(value), signal, fetcher), ms);
}
export async function cloudflare(env: AIEnv, model: string, value: Record<string, unknown>, ms = 18_000) {
  return timed(signal => cloudflareAdapter(env, model, input(value), signal), ms);
}
/** Kept for existing server callers; task integrations use generate with validators. */
export async function fallback<T>(primary: () => Promise<T>, secondary: () => Promise<T>): Promise<T> {
  try {return await primary();} catch (e) {if (!(e instanceof ProviderError) || !e.retryable) throw e; return secondary();}
}
export async function listeningInference<T = unknown>(env: AIEnv, value: Record<string, unknown>, validate: (output: unknown) => T = (o => {modelJSON(o); return o as T;})) {
  return ai.generate({env, task: 'listening_review', messages: input(value).messages, validate});
}
export async function readingInference<T = unknown>(env: AIEnv, value: Record<string, unknown>, validate: (output: unknown) => T = (o => {modelJSON(o); return o as T;})) {
  return ai.generate({env, task: 'smart_translate', messages: input(value).messages, validate});
}
export function modelJSON(output:unknown):unknown{
  if(!output||typeof output!=='object')throw new ProviderError(502);
  const o=output as {response?:unknown;choices?:{message?:{content?:unknown}}[]};
  const content=o.choices?.[0]?.message?.content??o.response;
  if(content&&typeof content==='object'&&!Array.isArray(content))return content;
  if(typeof content!=='string'||content.length>12_000)throw new ProviderError(502);
  const text=content.trim(),fence=/^```(?:json)?\s*([\s\S]*?)\s*```$/.exec(text);
  try{return JSON.parse(fence?fence[1]!:text);}catch{throw new ProviderError(502);}
}

export function reviewJSON(output:unknown){
 const parsed=modelJSON(output);
 if(!parsed||typeof parsed!=='object'||Array.isArray(parsed))throw new ProviderError(502);
 const p=parsed as Record<string,unknown>;
 if(Object.keys(p).sort().join(',')!=='next_time,quote,segment_ids,what_happened,why'||!['what_happened','why','next_time','quote'].every(k=>typeof p[k]==='string'&&(p[k] as string).length<=1800)||!Array.isArray(p.segment_ids)||p.segment_ids.length>5||!p.segment_ids.every(id=>typeof id==='string'&&/^seg-\d{4}$/.test(id)))throw new ProviderError(502);
 if(!['what_happened','why','next_time'].every(k=>/[А-Яа-яЁё]/.test(p[k] as string)))throw new ProviderError(502);
 return p;
}
