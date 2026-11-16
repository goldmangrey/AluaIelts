// Isolated native preview only; never calls a learner assessment route. No automatic retries.
import fs from 'node:fs';
import path from 'node:path';
const dir=process.env.WRITING_V3_QA_DIR,origin=process.env.WRITING_V3_QA_ORIGIN;
if(!dir||!origin||!/^https:\/\/[a-z0-9-]+\.yeskendiriskakov\.workers\.dev$/.test(origin))throw Error('Explicit isolated preview origin and shared budget directory required');
const provider=process.argv[2],fixture=process.argv[3];if(!['groq','cloudflare'].includes(provider)||!['advertising','weak','medium','strong','grammar','injection'].includes(fixture))throw Error('Unknown QA case');
const token=fs.readFileSync(path.join(dir,'token-private.txt'),'utf8'),ledger=path.join(dir,'calls.json');
const lock=fs.openSync(path.join(dir,'budget.lock'),'wx',0o600);let calls;
try{calls=fs.existsSync(ledger)?JSON.parse(fs.readFileSync(ledger,'utf8')):[];if(calls.length>=8)throw Error('Eight-call budget exhausted');calls.push({number:calls.length+1,provider,fixture,started_at:new Date().toISOString(),origin});fs.writeFileSync(ledger,JSON.stringify(calls,null,2),{mode:0o600});}finally{fs.closeSync(lock);fs.unlinkSync(path.join(dir,'budget.lock'));}
const number=calls.length;let body,status;
try{const response=await fetch(`${origin}/qa/${provider}/${fixture}`,{method:'POST',headers:{'X-QA-Token':token},signal:AbortSignal.timeout(55000)});status=response.status;body=await response.json();}catch(e){status=0;body={contract:'FAIL',reason:e.name};}
fs.writeFileSync(path.join(dir,`call-${number}-${provider}-${fixture}.json`),JSON.stringify({number,status,...body},null,2),{mode:0o600});
console.log(JSON.stringify({number,provider,fixture,status,contract:body.contract,reason:body.reason,criteria:body.review?.criteria.map(({name,band,limitations})=>({name,band,limitations})),issues:body.review?.issues.length,improvements:body.review?.top_improvements.length}));
