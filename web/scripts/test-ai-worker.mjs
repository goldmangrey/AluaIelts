// Real workerd execution, synthetic adapters, no remote bindings or provider quota.
import {spawn} from 'node:child_process';
import {createRequire} from 'node:module';
import {mkdtemp,writeFile,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join,resolve,dirname} from 'node:path';
import assert from 'node:assert/strict';
const require=createRequire(import.meta.url),temp=await mkdtemp(join(tmpdir(),'alua-ai-worker-'));
const config=join(temp,'wrangler.json');
await writeFile(config,JSON.stringify({name:'alua-ai-local-tests',main:resolve('tests/fixtures/ai-worker.ts'),compatibility_date:'2026-10-23',compatibility_flags:['nodejs_compat']}));
const child=spawn(process.execPath,[join(dirname(require.resolve('wrangler/package.json')),'bin/wrangler.js'),'dev','--config',config,'--local','--ip','127.0.0.1','--port','8876','--persist-to',join(temp,'state')],{env:{...process.env,WRANGLER_SEND_METRICS:'false'},stdio:['ignore','pipe','pipe']});
let log='';child.stdout.on('data',d=>{log+=d;});child.stderr.on('data',d=>{log+=d;});
try {
  let ready=false;
  for(let n=0;n<150;n++){
    try{const r=await fetch('http://127.0.0.1:8876');if(r.ok){ready=true;break;}}catch{}
    if(child.exitCode!==null)throw Error(log.slice(-2500));
    await new Promise(r=>setTimeout(r,200));
  }
  assert(ready,log.slice(-2500));
  for(const task of ['smart_translate','reading_review'])for(let fail=0;fail<=4;fail++){
    const response=await fetch(`http://127.0.0.1:8876?fail=${fail}&task=${task}`),body=await response.json();
    assert.equal(response.status,fail===4?503:200);
    assert.deepEqual(body.calls,['groq','cloudflare','gemini','openrouter'].slice(0,Math.min(fail+1,4)));
    if(fail<4)assert.equal(body.result.translation,'контекст');
  }
  console.log('10 PASS — native workerd sequential AI fallback and controlled failure');
}finally{
  child.kill('SIGTERM');
  if(child.exitCode===null)await new Promise(done=>child.once('exit',done));
  await rm(temp,{recursive:true,force:true});
}
