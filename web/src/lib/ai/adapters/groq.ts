import {type AIEnv, type AdapterInput, ProviderError, requestJSON, chatOutput} from './common';
export const groqAdapter = async (env: AIEnv, model: string, input: AdapterInput, signal: AbortSignal, fetcher: typeof fetch = fetch) => {
  if (!env.GROQ_API_KEY?.trim()) throw new ProviderError(503, true, 'configuration_failure');
  if(input.writingSchema&&model!=='openai/gpt-oss-120b')throw new ProviderError(503,false,'writing_schema_model');
  const data=await requestJSON('https://api.groq.com/openai/v1/chat/completions', {
    method: 'POST', signal, headers: {Authorization: `Bearer ${env.GROQ_API_KEY}`, 'Content-Type': 'application/json'},
    body: JSON.stringify({model, messages: input.messages, temperature: input.temperature,
      response_format: input.writingSchema?{type:'json_schema',json_schema:{name:'alua_writing_v4',strict:true,schema:input.writingSchema}}:{type:'json_object'}, reasoning_effort: 'low', include_reasoning: false,
      max_completion_tokens: Math.max(input.maxTokens, 1200), stream: false}),
  }, fetcher);
  const output=chatOutput(data);
  return input.writingSchema?{...output,usage:(data as {usage?:unknown}).usage??null}:output;
};
