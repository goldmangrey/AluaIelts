// Test-only sandbox; production Firebase/client modules are never edited.
import {mkdtemp,cp,symlink,mkdir,writeFile,rm} from "node:fs/promises";
import {tmpdir} from "node:os";
import {dirname,join,resolve} from "node:path";
import {fileURLToPath} from "node:url";
import {createRequire} from "node:module";
import {spawn} from "node:child_process";
const root=resolve(dirname(fileURLToPath(import.meta.url)),".."),require=createRequire(import.meta.url);
if(!process.env.ALUA_LISTENING_TEST_TOKEN?.startsWith("alua_dev_"))throw Error("Run through disposable backend pytest fixture only.");
const sandbox=await mkdtemp(join(tmpdir(),"alua-listening-browser-"));
const env={...process.env,ALUA_LISTENING_TEST_APP:sandbox,NEXT_PUBLIC_API_BASE_URL:"http://127.0.0.1:3401/api/v1"};
for(const name of Object.keys(env))if(name.startsWith("NEXT_PUBLIC_FIREBASE"))env[name]="";
async function file(name,text){const path=join(sandbox,name);await mkdir(dirname(path),{recursive:true});await writeFile(path,text);}
function run(cmd,args,cwd){return new Promise((done,fail)=>{const child=spawn(cmd,args,{cwd,env,stdio:"inherit"});child.on("error",fail);child.on("exit",code=>code===0?done():fail(Error(`Local browser verification exited ${code}`)));});}
try{
 for(const name of ["src","public","package.json","tsconfig.json","next.config.ts","postcss.config.mjs"])await cp(join(root,name),join(sandbox,name),{recursive:true});
 await symlink(join(root,"node_modules"),join(sandbox,"node_modules"),"dir");
 await file("src/lib/firebase/client.ts",`import type {Auth} from "firebase/auth";
export function firebaseConfigured(){return true}
export async function getFirebaseAuth():Promise<Auth>{throw Error("Test-only session")}
export async function getIdToken(_force=false,_expectedUid?:string){return ${JSON.stringify(process.env.ALUA_LISTENING_TEST_TOKEN)}}`);
 await file("src/features/auth/session.ts",`"use client";
import {useSyncExternalStore} from "react";
export interface Session {status:"loading"|"signed_out"|"ready"|"error";user:{uid:string;email:string|null}|null;profile:import("./api").LearnerProfile|null;error?:unknown;generation:number};
const initial:Session={status:"loading",user:null,profile:null,generation:0};
const ready:Session={status:"ready",user:{uid:"listening-fixture",email:"fixture@example.invalid"},profile:null,generation:1};
export function useSession(){return useSyncExternalStore(()=>()=>{},()=>ready,()=>initial)}
export async function prepareGoogleAuth(_mode?:string){return async()=>{}};export async function retrySession(){};export async function logout(){};export async function authenticate(..._args:unknown[]){};export function rejectSession(_generation:number){};`);
 await run(process.execPath,[require.resolve("next/dist/bin/next"),"build","--webpack"],sandbox);
 await run(process.execPath,[join(dirname(require.resolve("@playwright/test/package.json")),"cli.js"),"test","--config=playwright.listening.config.ts"],root);
}finally{await rm(sandbox,{recursive:true,force:true});}
