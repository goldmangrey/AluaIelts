// Optional single-call capture. No learner attempt, database, retry, fallback chain or AI judge.
// Human review must inspect the captured output; contract success is not quality success.
import fs from 'node:fs';
import path from 'node:path';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
const web=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..'),req=createRequire(web+'/package.json'),ts=req('typescript');
const dir=process.env.WRITING_LIVE_QA_OUTPUT;if(!dir)throw Error('Set an explicit private QA output directory');
fs.mkdirSync(dir,{recursive:true});const modules=new Map();
function load(file){if(modules.has(file))return modules.get(file);const exports={};modules.set(file,exports);const code=ts.transpileModule(fs.readFileSync(file,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;new Function('require','exports','process',code)(id=>id.startsWith('.')?load(path.resolve(path.dirname(file),id)+'.ts'):req(id),exports,process);return exports;}
const {writingPrompt}=load(web+'/src/features/writing/prompt.ts'),{evidenceCandidates,validateModelReview}=load(web+'/src/features/writing/contract.ts'),{cloudflareAdapter}=load(web+'/src/lib/ai/adapters/cloudflare.ts'),{tasks,models}=load(web+'/src/lib/ai/tasks.ts');
const fixture=JSON.parse(fs.readFileSync(web+'/tests/fixtures/writing-advertising-v2.json'));
const config=path.join(dir,'wrangler.json');fs.writeFileSync(config,JSON.stringify({name:'alua-writing-accuracy-qa',compatibility_date:'2026-10-23',compatibility_flags:['nodejs_compat'],ai:{binding:'AI',remote:true}}));
process.env.ALUA_LOCAL_STACK='true';const platform=await req('wrangler').getPlatformProxy({configPath:config,persist:false,remoteBindings:true,envFiles:[]});
let count=0;const result={provider:'cloudflare',model:models.cloudflare,live_quality:'NOT VERIFIED',actual_ai_calls:0};
try{
 // Exclusive latch prevents a rerun from silently spending a second call.
 fs.closeSync(fs.openSync(path.join(dir,'one-call-spent'),'wx',0o600));count++;result.actual_ai_calls=count;
 const raw=await cloudflareAdapter(platform.env,models.cloudflare,{temperature:tasks.writing_assessment.temperature,maxTokens:tasks.writing_assessment.tokens,messages:[{role:'system',content:writingPrompt},{role:'user',content:JSON.stringify({task:{practice_prompt:fixture.prompt,task_requirements:['Discuss both views','Give your own opinion']},essay:fixture.essay,evidence_candidates:evidenceCandidates(fixture.essay).map((a,i)=>({candidate_id:`s${i}`,quote:a.quote}))})}]},AbortSignal.timeout(60000));
 fs.writeFileSync(path.join(dir,'raw.json'),JSON.stringify(raw,null,2),{mode:0o600});
 const review=validateModelReview(raw,fixture.essay);fs.writeFileSync(path.join(dir,'review.json'),JSON.stringify(review,null,2),{mode:0o600});
 result.contract='PASS';result.criteria=review.criteria.map(({name,band})=>({name,band}));result.issues=review.issues.length;result.improvements=review.top_improvements.length;
}catch(e){result.contract='FAIL';result.reason=e.message.slice(0,160);process.exitCode=1;}
finally{fs.writeFileSync(path.join(dir,'result.json'),JSON.stringify(result,null,2),{mode:0o600});await platform.dispose();console.log(JSON.stringify(result));}
