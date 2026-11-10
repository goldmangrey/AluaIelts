import {type Adapter, type AdapterInput, type AIEnv, type Provider, ProviderError, timed} from './adapters/common';
import {groqAdapter} from './adapters/groq';
import {cloudflareAdapter} from './adapters/cloudflare';
import {geminiAdapter} from './adapters/gemini';
import {openrouterAdapter} from './adapters/openrouter';
import {candidates, tasks, type Task} from './tasks';
export {ProviderError} from './adapters/common';
const adapters = {groq: groqAdapter, cloudflare: cloudflareAdapter, gemini: geminiAdapter, openrouter: openrouterAdapter};
export interface Telemetry {task: Task; provider: Provider; model: string; outcome: string; latency_ms: number; fallback_reason: string | null}
/** A factory allows isolated mocks; production uses exactly one per-isolate instance. */
export function createAI(options: {adapters?: Partial<Record<Provider, Adapter>>; now?: () => number; log?: (event: Telemetry) => void} = {}) {
  const cooldown = new Map<string, number>(), now = options.now ?? (() => performance.now());
  const log = options.log ?? ((event: Telemetry) => console.info('[ai]', event));
  return {async generate<T>({env, task, messages, validate}: {env: AIEnv; task: Task; messages: AdapterInput['messages']; validate: (output: unknown) => T}): Promise<T> {
    const route = tasks[task];
    if (!route?.active || !messages.length || messages.length > 8 || messages.some(m => !['system','user','assistant'].includes(m.role) || typeof m.content !== 'string') ||
        new TextEncoder().encode(JSON.stringify(messages)).length > 96_000) throw new ProviderError(503, false, 'invalid_task_input');
    const until = now() + route.deadline;
    for (const [key, expires] of cooldown) if (expires <= now()) cooldown.delete(key);
    let invalid: ProviderError | undefined;
    const eligible = candidates(task, env);
    for (const candidate of eligible) {
      const {provider, model} = candidate, key = `${provider}:${model}`, start = now();
      if ((cooldown.get(key) ?? 0) > start) {log({task, provider, model, outcome: 'skipped', latency_ms: 0, fallback_reason: 'cooldown'}); continue;}
      const remaining = until - start;
      if (remaining < 250) break;
      try {
        const result = await timed(async signal => {
          const output = await (options.adapters?.[provider] ?? adapters[provider])(env, model,
            {messages, maxTokens: route.tokens, temperature: route.temperature}, signal);
          try {
            const value = validate(output);
            if (value === null || value === undefined || value === false) throw Error();
            return value;
          } catch (error) {throw error instanceof ProviderError && ['invalid_model_json','invalid_translation'].includes(error.reason) ? error : new ProviderError(502, true, 'invalid_output');}
        }, Math.min(candidate.provider === 'cloudflare' && eligible.length === 2 ? (task === 'listening_review' ? 18_000 : remaining) : candidate.timeout, remaining));
        if (now() >= until) throw new ProviderError(504, true, 'deadline');
        log({task, provider, model, outcome: 'success', latency_ms: Math.round(now() - start), fallback_reason: null});
        return result;
      } catch (error) {
        const e = error instanceof ProviderError ? error : new ProviderError(503, true, 'network_error');
        if (['invalid_output','invalid_model_json','invalid_translation'].includes(e.reason)) invalid = e;
        log({task, provider, model, outcome: 'failure', latency_ms: Math.round(now() - start), fallback_reason: e.reason});
        // Configuration/model errors also advance, never become user authentication errors.
        if (e.status === 429 || [408,500,502,503,504].includes(e.status) && !['invalid_output','invalid_model_json','invalid_translation','configuration_failure'].includes(e.reason)) {
          if (cooldown.size >= 64) cooldown.clear();
          cooldown.set(key, now() + (e.status === 429 ? Math.max(1000, e.retryAfterMs || 30_000) : 2000));
        }
      }
    }
    if (invalid) throw invalid;
    throw new ProviderError(503, false, 'all_providers_unavailable');
  }};
}
export const ai = createAI();
