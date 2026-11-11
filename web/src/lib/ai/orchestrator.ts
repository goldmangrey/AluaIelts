import {type Adapter, type AdapterInput, type AIEnv, type Provider, ProviderError, timed} from './adapters/common';
import {groqAdapter} from './adapters/groq';
import {cloudflareAdapter} from './adapters/cloudflare';
import {geminiAdapter} from './adapters/gemini';
import {openrouterAdapter} from './adapters/openrouter';
import {candidates, tasks, type Task} from './tasks';
export {ProviderError} from './adapters/common';
const adapters = {groq: groqAdapter, cloudflare: cloudflareAdapter, gemini: geminiAdapter, openrouter: openrouterAdapter};
export interface Telemetry {task: Task; provider: Provider; model: string; outcome: string; latency_ms: number; fallback_reason: string | null; http_status?:number; request_id?:string}
/** A factory allows isolated mocks; production uses exactly one per-isolate instance. */
export function createAI(options: {adapters?: Partial<Record<Provider, Adapter>>; now?: () => number; log?: (event: Telemetry) => void} = {}) {
  const cooldown = new Map<string, {until:number;status:number;retryUntil?:number;requestId?:string}>(), now = options.now ?? (() => performance.now());
  const log = options.log ?? ((event: Telemetry) => console.info('[ai]', event));
  return {async generate<T>({env, task, messages, validate, deadlineMs, onSuccess, onAttempt}: {env: AIEnv; task: Task; deadlineMs?:number; onSuccess?:(event:Telemetry)=>void; onAttempt?:(provider:Provider)=>void; messages: AdapterInput['messages']; validate: (output: unknown) => T}): Promise<T> {
    const route = tasks[task];
    if (!route?.active || !messages.length || messages.length > 8 || messages.some(m => !['system','user','assistant'].includes(m.role) || typeof m.content !== 'string') ||
        new TextEncoder().encode(JSON.stringify(messages)).length > 96_000) throw new ProviderError(503, false, 'invalid_task_input');
    const until = now() + Math.min(route.deadline, Math.max(0,deadlineMs??route.deadline));
    for (const [key, expires] of cooldown) if (expires.until <= now()) cooldown.delete(key);
    let invalid: ProviderError | undefined,abstained=false,timedOut=false;const rateLimits:ProviderError[]=[];
    const eligible = candidates(task, env);
    for (const candidate of eligible) {
      const {provider, model} = candidate, key = `${provider}:${model}`, start = now();
      const held=cooldown.get(key);if (held&&held.until>start) {if(held.status===429)rateLimits.push(new ProviderError(429,true,'provider_rate_limited',held.retryUntil?Math.max(0,held.retryUntil-start):0,held.requestId));log({task, provider, model, outcome: 'skipped', latency_ms: 0, fallback_reason: 'cooldown'}); continue;}
      const remaining = until - start;
      if (remaining < 250) {timedOut=true;break;}
      try {
        const result = await timed(async signal => {
          const configured=provider==='cloudflare'?!!env.AI:!!env[provider==='groq'?'GROQ_API_KEY':provider==='gemini'?'GEMINI_API_KEY':'OPENROUTER_API_KEY']?.trim();
          if(configured||options.adapters?.[provider])onAttempt?.(provider);
          const output = await (options.adapters?.[provider] ?? adapters[provider])(env, model,
            {messages, maxTokens: route.tokens, temperature: route.temperature}, signal);
          try {
            const value = validate(output);
            if (value === null || value === undefined || value === false) throw Error();
            return value;
          } catch (error) {throw error instanceof ProviderError && ['invalid_model_json','invalid_translation','model_abstained'].includes(error.reason) ? error : new ProviderError(502, true, 'invalid_output');}
        }, Math.min(candidate.provider === 'cloudflare' && eligible.length === 2 ? (task === 'listening_review' ? 18_000 : remaining) : candidate.timeout, remaining));
        if (now() >= until) throw new ProviderError(504, true, 'deadline');
        const event:Telemetry={task, provider, model, outcome: 'success', latency_ms: Math.round(now() - start), fallback_reason: null};
        log(event);onSuccess?.(event);
        return result;
      } catch (error) {
        const e = error instanceof ProviderError ? error : new ProviderError(503, true, 'network_error');
        if([408,504].includes(e.status))timedOut=true;
        if(e.reason==='model_abstained')abstained=true;
        if (['invalid_output','invalid_model_json','invalid_translation','invalid_json','empty_output','output_too_large'].includes(e.reason)) invalid = e;
        if(e.status===429)rateLimits.push(e);
        log({task, provider, model, outcome: 'failure', latency_ms: Math.round(now() - start), fallback_reason: e.reason,http_status:e.status,...(e.requestId?{request_id:e.requestId}:{})});
        // Configuration/model errors also advance, never become user authentication errors.
        if (e.status === 429 || [408,500,502,503,504].includes(e.status) && !['invalid_output','invalid_model_json','invalid_translation','model_abstained','configuration_failure'].includes(e.reason)) {
          if (cooldown.size >= 64) cooldown.clear();
          const at=now();cooldown.set(key,{until:at+(e.status===429?Math.max(1000,e.retryAfterMs||30_000):2000),status:e.status,...(e.requestId?{requestId:e.requestId}:{}),...(e.status===429&&e.retryAfterMs>0?{retryUntil:at+e.retryAfterMs}:{})});
        }
      }
    }
    if (invalid) throw invalid;
    if(rateLimits.length){const known=rateLimits.every(e=>e.retryAfterMs>0)?Math.min(...rateLimits.map(e=>e.retryAfterMs)):0;throw new ProviderError(429,true,'provider_rate_limited',known,rateLimits.find(e=>e.requestId)?.requestId);}
    if(timedOut||now()>=until)throw new ProviderError(504,false,"timeout");
    throw new ProviderError(503, false, abstained?'model_abstained':'all_providers_unavailable');
  }};
}
export const ai = createAI();
