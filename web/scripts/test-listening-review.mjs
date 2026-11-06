// Disposable frontend sandbox: no database, backend server or real Firebase session.
import {mkdtemp,cp,symlink,mkdir,writeFile,readFile,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {dirname,join,resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {createRequire} from 'node:module';
import {spawn} from 'node:child_process';
const root=resolve(dirname(fileURLToPath(import.meta.url)),'..'),require=createRequire(import.meta.url);
const sandbox=await mkdtemp(join(tmpdir(),'alua-listening-review-'));
const env={...process.env,ALUA_REVIEW_TEST_APP:sandbox,NEXT_PUBLIC_API_BASE_URL:'http://127.0.0.1:3312/api/v1'};
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
 if(process.env.ALUA_REVIEW_PRODUCTION==='1')await new Promise((done,fail)=>{const child=spawn(process.execPath,[require.resolve('next/dist/bin/next'),'build','--webpack'],{cwd:sandbox,env,stdio:'inherit'});child.on('error',fail);child.on('exit',code=>code===0?done():fail(Error(`Sandbox build exited ${code}`)));});
 await new Promise((done,fail)=>{const child=spawn(process.execPath,[join(dirname(require.resolve('@playwright/test/package.json')),'cli.js'),'test','--config=playwright.listening-review.config.ts',...process.argv.slice(2)],{cwd:root,env,stdio:'inherit'});child.on('error',fail);child.on('exit',code=>code===0?done():fail(Error(`Review browser checks exited ${code}`)));});
} finally {await rm(sandbox,{recursive:true,force:true});}
