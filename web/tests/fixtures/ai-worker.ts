/** Disposable local workerd fixture; never part of the Next app or deployed Worker. */
import {createAI} from '../../src/lib/ai/orchestrator';
import {type Provider, type Adapter, ProviderError} from '../../src/lib/ai/adapters/common';
import {modelJSON} from '../../src/lib/ai/providers';
const order: Provider[] = ['groq','cloudflare','gemini','openrouter'];
const worker = {async fetch(request: Request) {
  const task=new URL(request.url).searchParams.get('task')==='reading_review'?'reading_review':'smart_translate';
  const failCount = Number(new URL(request.url).searchParams.get('fail') ?? 0), calls: string[] = [];
  const mock = (provider: Provider): Adapter => async () => {
    calls.push(provider);
    if (order.indexOf(provider) < failCount) throw new ProviderError(429, true, 'http_429');
    return {response: '{"translation":"контекст","expression":"context"}'};
  };
  const ai = createAI({adapters: {groq:mock('groq'),cloudflare:mock('cloudflare'),gemini:mock('gemini'),openrouter:mock('openrouter')},log:()=>{}});
  try {
    const result = await ai.generate({env:{AI_EXTERNAL_TASKS:task},task,messages:[{role:'user',content:'Synthetic fixture'}],validate:modelJSON});
    return Response.json({result,calls});
  } catch {return Response.json({error:'ai_unavailable',calls},{status:503});}
}};

export default worker;
