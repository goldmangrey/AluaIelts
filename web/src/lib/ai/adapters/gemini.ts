import {type Adapter, ProviderError, requestJSON} from './common';
export const geminiAdapter: Adapter = async (env, model, input, signal) => {
  if (!env.GEMINI_API_KEY?.trim() || !/^[a-z0-9.-]+$/.test(model)) throw new ProviderError(503, true, 'configuration_failure');
  const system = input.messages.filter(m => m.role === 'system').map(m => ({text: m.content}));
  const data = await requestJSON(`https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent`, {
    method: 'POST', signal, headers: {'x-goog-api-key': env.GEMINI_API_KEY, 'Content-Type': 'application/json'},
    body: JSON.stringify({
      ...(system.length ? {systemInstruction: {parts: system}} : {}),
      contents: input.messages.filter(m => m.role !== 'system').map(m => ({role: m.role === 'assistant' ? 'model' : 'user', parts: [{text: m.content}]})),
      generationConfig: {temperature: input.temperature, maxOutputTokens: input.maxTokens, responseMimeType: 'application/json'},
    }),
  }) as {candidates?: {finishReason?: string; content?: {parts?: {text?: string; thought?: boolean}[]}}[]};
  const candidate = data?.candidates?.[0];
  const text = candidate?.content?.parts?.filter(p => !p.thought).map(p => p.text ?? '').join('');
  if (candidate?.finishReason !== 'STOP' || !text?.trim() || text.length > 12_000) throw new ProviderError(502, true, 'invalid_output');
  return {response: text};
};
