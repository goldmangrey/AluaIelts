import {type AIEnv, type AdapterInput, ProviderError, requestJSON, chatOutput} from './common';
export const groqAdapter = async (env: AIEnv, model: string, input: AdapterInput, signal: AbortSignal, fetcher: typeof fetch = fetch) => {
  if (!env.GROQ_API_KEY?.trim()) throw new ProviderError(503, true, 'configuration_failure');
  return chatOutput(await requestJSON('https://api.groq.com/openai/v1/chat/completions', {
    method: 'POST', signal, headers: {Authorization: `Bearer ${env.GROQ_API_KEY}`, 'Content-Type': 'application/json'},
    body: JSON.stringify({model, messages: input.messages, temperature: input.temperature,
      response_format: {type: 'json_object'}, reasoning_effort: 'low', include_reasoning: false,
      max_completion_tokens: Math.max(input.maxTokens, 1200), stream: false}),
  }, fetcher));
};
