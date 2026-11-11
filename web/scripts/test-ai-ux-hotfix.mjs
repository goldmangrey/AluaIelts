// Disposable frontend sandbox: no database, backend server or real Firebase session.
import {mkdtemp,cp,symlink,mkdir,writeFile,readFile,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {dirname,join,resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {createRequire} from 'node:module';
import {spawn} from 'node:child_process';
const root=resolve(dirname(fileURLToPath(import.meta.url)),'..'),require=createRequire(import.meta.url);
const sandbox=await mkdtemp(join(tmpdir(),'alua-ai-ux-'));
const env={...process.env,ALUA_REVIEW_TEST_APP:sandbox,NEXT_PUBLIC_API_BASE_URL:'http://127.0.0.1:3315/api/v1'};
for(const name of Object.keys(env))if(name.startsWith('NEXT_PUBLIC_FIREBASE'))env[name]='';
async function file(name,text){const path=join(sandbox,name);await mkdir(dirname(path),{recursive:true});await writeFile(path,text);}
try {
 for(const name of ['src','public','package.json','tsconfig.json','next.config.ts','postcss.config.mjs'])await cp(join(root,name),join(sandbox,name),{recursive:true});
 await file('next.config.ts',(await readFile(join(root,'next.config.ts'),'utf8')).replace('const config: NextConfig = {','const config: NextConfig = { devIndicators: false,'));
 await symlink(join(root,'node_modules'),join(sandbox,'node_modules'),'dir');
 await file('src/lib/firebase/client.ts',`import type {Auth} from 'firebase/auth';
export function firebaseConfigured(){return true}
export async function getFirebaseAuth():Promise<Auth>{throw Error('Isolated review fixture')}
export async function getIdToken(_force=false,_expectedUid?:string){return 'review-fixture-only'}`);
 await file('src/features/auth/session.ts',`"use client";
import {useSyncExternalStore} from 'react';
export interface Session {status:'loading'|'signed_out'|'ready'|'error';user:{uid:string;email:string|null}|null;profile:import('./api').LearnerProfile|null;error?:unknown;generation:number}
const initial:Session={status:'loading',user:null,profile:null,generation:0};
const ready:Session={status:'ready',user:{uid:'review-fixture',email:null},profile:null,generation:1};
export function useSession(){return useSyncExternalStore(()=>()=>{},()=>ready,()=>initial)}
export async function prepareGoogleAuth(_mode?:string){return async()=>{}};export async function retrySession(){};export async function logout(){};export async function authenticate(..._args:unknown[]){};export function rejectSession(_generation:number){};`);
 await file('src/app/ai-ux-fixture/page.tsx',`"use client";
import {QuestionGroup,type QuestionActions} from '@/features/reading/exam/question-renderer';
import type {Group,Constraints} from '@/features/reading/exam/models';
const constraints:Constraints={max_words:2,allow_number:false,allowed_values:[],reuse_allowed:true,selection_count:null};
export default function Fixture(){
 const answers:Record<string,string>={q1:'A',q2:'B',q3:'',q4:'B',q5:'A',q6:'word',q7:'wrong',q8:''};
 const results=Array.from({length:8},(_,i)=>({question_id:'q'+(i+1),number:i+1,passage_number:1,user_answer:answers['q'+(i+1)]!,correct_answer:i<5?(i===4?'B':'A'):'word',accepted_answers:[i<5?(i===4?'B':'A'):'word'],is_correct:[0,3,4,5].includes(i),unanswered:[2,7].includes(i),unordered_group:i===3||i===4}));
 const groups:Group[]=[...[1,2,3].map(n=>({id:'g'+n,type:'multiple_choice_single' as const,question_numbers:[n],instructions:'Choose the correct answer.',constraints,assets:[],representation:'structured_text' as const,options:[],content_blocks:[],questions:[{id:'q'+n,number:n,group_id:'g'+n,type:'multiple_choice_single' as const,prompt:'Synthetic choice',answer_input_type:'single_select' as const,constraints,options:[{label:'A',text:'Correct option'},{label:'B',text:'Other option'}]}]})),
 {id:'multi',type:'multiple_choice_multiple',question_numbers:[4,5],instructions:'Choose two letters.',constraints:{...constraints,selection_count:2},assets:[],representation:'structured_text',options:[{label:'A',text:'One'},{label:'B',text:'Two'},{label:'C',text:'Three'}],content_blocks:[],questions:[4,5].map(n=>({id:'q'+n,number:n,group_id:'multi',type:'multiple_choice_multiple',prompt:'Choose two letters.',answer_input_type:'multi_select',constraints,options:[]}))},
 {id:'inline',type:'summary_completion',question_numbers:[6,7,8],instructions:'Complete the summary. Write no more than two words.',constraints,assets:[],representation:'structured_text',options:[],content_blocks:[{type:'rich_text',segments:[{type:'text',text:'A readable sentence '},{type:'blank',number:6},{type:'text',text:' then '},{type:'blank',number:7},{type:'text',text:' and '},{type:'blank',number:8},{type:'text',text:'.'}]}],questions:[6,7,8].map(n=>({id:'q'+n,number:n,group_id:'inline',type:'summary_completion',prompt:'Complete the summary.',answer_input_type:'text',constraints,options:[]}))}];
 const actions:QuestionActions={results,answers,review:new Set(),locked:new Set(),disabled:true,change:()=>{},toggleReview:()=>{},register:()=>{},focus:()=>{}};
 return <main style={{padding:24}}>{groups.map(group=><QuestionGroup key={group.id} group={group} actions={actions} uid="synthetic-fixture"/>)}</main>;
}`);
 if(process.env.ALUA_REVIEW_PRODUCTION==='1')await new Promise((done,fail)=>{const child=spawn(process.execPath,[require.resolve('next/dist/bin/next'),'build','--webpack'],{cwd:sandbox,env,stdio:'inherit'});child.on('error',fail);child.on('exit',code=>code===0?done():fail(Error(`Sandbox build exited ${code}`)));});
 await new Promise((done,fail)=>{const child=spawn(process.execPath,[join(dirname(require.resolve('@playwright/test/package.json')),'cli.js'),'test','--config=playwright.ai-ux.config.ts',...process.argv.slice(2)],{cwd:root,env,stdio:'inherit'});child.on('error',fail);child.on('exit',code=>code===0?done():fail(Error(`Review browser checks exited ${code}`)));});
} finally {await rm(sandbox,{recursive:true,force:true});}
