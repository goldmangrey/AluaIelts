import type {AIEnv, Provider} from './adapters/common';
const order: Provider[] = ['groq', 'cloudflare', 'gemini', 'openrouter'];
export const models = {groq: 'openai/gpt-oss-120b', cloudflare: '@cf/google/gemma-4-26b-a4b-it',
  gemini: 'gemini-3.5-flash-lite', openrouter: 'google/gemma-4-26b-a4b-it:free'} as const;
// Keep 120B for translation until 20B quality has been verified. Models are task-specific.
export const tasks = {
  listening_review: {active: true, sensitive: true, deadline: 45_000, tokens: 1800, temperature: .2, attempts: [18_000,12_000,8_000,7_000], models},
  smart_translate: {active: true, sensitive: true, deadline: 15_000, tokens: 160, temperature: 0, attempts: [5000,4000,3000,3000], models: {...models}},
  // Backend migrations stay disabled until a dedicated service credential and policy exist.
  ai_progress_report: {active: false, sensitive: true, deadline: 0, tokens: 0, temperature: 0, attempts: [], models},
  ai_progress_chat: {active: false, sensitive: true, deadline: 0, tokens: 0, temperature: 0, attempts: [], models},
  exercise_generation: {active: false, sensitive: true, deadline: 0, tokens: 0, temperature: 0, attempts: [], models},
  reading_review: {active: true, sensitive: true, deadline: 45_000, tokens: 2400, temperature: .2, attempts: [18_000,12_000,8_000,7_000], models},
  writing_assessment: {active: false, sensitive: true, deadline: 0, tokens: 0, temperature: 0, attempts: [], models},
  speaking_assessment: {active: false, sensitive: true, deadline: 0, tokens: 0, temperature: 0, attempts: [], models},
} as const;
export type Task = keyof typeof tasks;
export function candidates(task: Task, env: AIEnv) {
  const route = tasks[task];
  if (!route.active) return [];
  const externalAllowed = !route.sensitive || (env.AI_EXTERNAL_TASKS ?? '').split(',').map(s => s.trim()).includes(task);
  return order.filter(provider => {
    if (provider === 'groq') return true;
    if (provider === 'cloudflare') return true;
    if (!externalAllowed) return false;
    return provider === 'gemini' ? env.AI_GEMINI_ENABLED !== 'false' :
      env.AI_OPENROUTER_ENABLED !== 'false';
  }).map(provider => ({provider, model: provider === 'openrouter' ? env.AI_OPENROUTER_MODEL ?? route.models[provider] : route.models[provider],
    timeout: route.attempts[order.indexOf(provider)] ?? 0}));
}
