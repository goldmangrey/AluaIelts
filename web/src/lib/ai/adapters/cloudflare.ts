import {type Adapter, ProviderError, transient, chatOutput} from './common';
export const cloudflareAdapter: Adapter = async (env, model, input, signal) => {
  if (!env.AI) throw new ProviderError(503, true, 'configuration_failure');
  try {
    return chatOutput(await env.AI.run(model, {messages: input.messages, temperature: input.temperature,
      max_completion_tokens: input.maxTokens, response_format: {type: 'json_object'},
      chat_template_kwargs: {enable_thinking: false}, stream: false}, {signal}));
  } catch (error) {
    if (error instanceof ProviderError) throw error;
    const e = error as {status?: number; statusCode?: number; message?: string};
    const internal: Record<number, number> = {3036:429,3040:429,3007:408,3008:408,5018:403,5016:403,3023:403,3041:403,5035:403,5007:400,5004:400,3003:400,3042:404};
    const raw = Number(e.status ?? e.statusCode ?? /\b(3036|3040|3007|3008|5018|5016|3023|3041|5035|5007|5004|3003|3042|400|401|403|404|408|410|422|429|500|502|503|504)\b/.exec(e.message || '')?.[1]);
    const status = internal[raw] ?? (raw >= 100 && raw <= 599 ? raw : 502);
    throw new ProviderError(status, transient(status) || [401,403,404,410].includes(status),
      [401,403].includes(status) ? 'configuration_failure' : `http_${status}`);
  }
};
