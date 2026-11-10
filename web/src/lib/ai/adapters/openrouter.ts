import {type Adapter, ProviderError, requestJSON, chatOutput} from './common';
// Positive eligibility only; no stale-on-error cache and never a paid model substitution.
const eligible = new Map<string, number>();
export const openrouterAdapter: Adapter = async (env, model, input, signal) => {
  if (!env.OPENROUTER_API_KEY?.trim() || !/^[a-z0-9._-]+\/[a-z0-9._-]+:free$/.test(model)) throw new ProviderError(503, true, 'free_model_unavailable');
  if ((eligible.get(model) ?? 0) <= Date.now()) {
    const catalog = await requestJSON('https://openrouter.ai/api/v1/models', {signal}, fetch, 2_000_000) as {
      data?: {id: string; pricing?: Record<string, string>; supported_parameters?: string[]; architecture?: {output_modalities?: string[]}}[];
    };
    const entry = catalog.data?.find(m => m.id === model);
    if (!entry?.pricing || !['prompt','completion'].every(k => entry.pricing?.[k] === '0') ||
        Object.values(entry.pricing).some(v => !Number.isFinite(Number(v)) || Number(v) !== 0) ||
        !entry.supported_parameters?.includes('response_format') || !entry.architecture?.output_modalities?.includes('text'))
      throw new ProviderError(503, true, 'free_model_unavailable');
    if (eligible.size >= 16) eligible.clear();
    eligible.set(model, Date.now() + 60_000);
  }
  return chatOutput(await requestJSON('https://openrouter.ai/api/v1/chat/completions', {
    method: 'POST', signal, headers: {Authorization: `Bearer ${env.OPENROUTER_API_KEY}`, 'Content-Type': 'application/json'},
    body: JSON.stringify({model, messages: input.messages, temperature: input.temperature, max_tokens: input.maxTokens,
      response_format: {type: 'json_object'}, stream: false,
      provider: {require_parameters: true, data_collection: 'deny', max_price: {prompt: 0, completion: 0}}}),
  }));
};
