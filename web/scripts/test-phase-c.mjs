// Real local public content, isolated test-only routes, no production auth/writes.
import { mkdtemp, cp, symlink, rm, mkdir, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";
import { spawn } from "node:child_process";
const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const require = createRequire(import.meta.url);
const sandbox = await mkdtemp(join(tmpdir(), "alua-reading-tests-"));
const fixtures = join(sandbox, "reading-fixtures.json");
const screenshots = join(root, ".next/reading-qa-screenshots");
await mkdir(screenshots, { recursive: true });
const env = { ...process.env, ALUA_C_TEST_APP: sandbox, ALUA_C_FIXTURES: fixtures, ALUA_C_SCREENSHOTS: screenshots };
for (const key of Object.keys(env)) if (key.startsWith("NEXT_PUBLIC_")) env[key] = "";
if(process.env.ALUA_RELEASE_TEST)env.NEXT_PUBLIC_API_BASE_URL="http://127.0.0.1:3300/api/v1";
if(process.env.ALUA_INTEGRATION_TEST){
  if(process.env.ALUA_RELEASE_API_URL!=="http://127.0.0.1:3400/api/v1"||!process.env.ALUA_RELEASE_INTEGRATION_TOKEN)throw Error("Run integration via the disposable backend pytest fixture.");
  env.NEXT_PUBLIC_API_BASE_URL=process.env.ALUA_RELEASE_API_URL;
}
function run(command, args, cwd) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, { cwd, env, stdio: "inherit" });
    child.on("error", reject); child.on("exit", (code) => code === 0 ? resolve() : reject(new Error(`Reading verification exited with ${code}`)));
  });
}
async function file(name, content) { const p = join(sandbox, name); await mkdir(dirname(p), { recursive: true }); await writeFile(p, content); }
try {
  await run(join(root, "../backend/.venv/bin/python"), [join(root, "scripts/export-reading-fixtures.py"), fixtures], root);
  for (const name of ["src", "public", "package.json", "tsconfig.json", "next.config.ts", "postcss.config.mjs"])
    await cp(join(root, name), join(sandbox, name), { recursive: true });
  await symlink(join(root, "node_modules"), join(sandbox, "node_modules"), "dir");
  await file("src/app/reading-qa/[examId]/page.tsx", `import {readFile} from "node:fs/promises";
import {notFound} from "next/navigation";
import {Harness} from "../harness";
import {parseExam} from "@/features/reading/exam/parse";
export default async function Page({params}:{params:Promise<{examId:string}>}) {
const {examId}=await params;
const data=JSON.parse(await readFile(process.env.ALUA_C_FIXTURES!,"utf8"));
const exam=data.exams.find((e:{id:string})=>e.id===examId);if(!exam)notFound();
return <Harness exam={parseExam(exam)} now={data.now} deadline={data.deadline}/>;
}`);
  await file("src/app/reading-qa/harness.tsx", `"use client";
import {useSyncExternalStore} from "react";
import {ReadingExam} from "@/features/reading/exam/reading-exam";
import {AssetLoaderContext} from "@/features/reading/exam/asset-image";
import {parseAttempt} from "@/features/reading/exam/parse";
import {ApiError} from "@/lib/api/client";
import type {Exam,Attempt} from "@/features/reading/exam/models";
const loadAsset=async(id:string,signal:AbortSignal)=>{const r=await fetch("/reading-qa/asset/"+encodeURIComponent(id),{signal});if(!r.ok)throw Error("Image missing");return r.blob()};
export function Harness({exam,now,deadline}:{exam:Exam;now:string;deadline:string}) {
const ready=useSyncExternalStore(()=>()=>{},()=>true,()=>false);
const first=exam.passages[0]!.question_groups[0]!.questions[0]!;
const attempt:Attempt={id:"11111111-2222-4333-8444-555555555555",exam_id:exam.id,mode:"full_exam",status:"in_progress",version:7,content_hash:"fixture-hash",server_now:now,deadline_at:deadline,answers:first.answer_input_type==="text"?{[first.id]:"restored draft"}:{},state:{current_passage:1,checked_question_ids:[]},not_fully_proofread:true,exam};
if(!ready)return <p role="status">Loading isolated Reading fixture…</p>;
return <AssetLoaderContext.Provider value={loadAsset}><ReadingExam uid="isolated-fixture-user" attempt={attempt} save={async(event)=>{
const r=await fetch("/reading-qa/save",{method:"POST",body:JSON.stringify(event)});if(!r.ok)throw new ApiError(r.status,r.status===409?"reading_version_conflict":"test_save_failure");return parseAttempt(await r.json());
}}/></AssetLoaderContext.Provider>;
}`);
  await file("src/app/reading-qa/asset/[assetId]/route.ts", `import {readFile} from "node:fs/promises";
export async function GET(_req:Request,{params}:{params:Promise<{assetId:string}>}) { const {assetId}=await params;
const data=JSON.parse(await readFile(process.env.ALUA_C_FIXTURES!,"utf8")); const path=data.assets[assetId];if(!path)return new Response(null,{status:404});
return new Response(await readFile(path),{headers:{"Content-Type":"image/png","Cache-Control":"no-store"}});
}`);
  if(process.env.ALUA_RELEASE_TEST) {
    await file("src/lib/firebase/client.ts", `import type {Auth} from "firebase/auth";
export function firebaseConfigured(){return true}
export async function getFirebaseAuth():Promise<Auth>{throw Error("Isolated fixture only")}
export async function getIdToken(_force=false,expectedUid?:string){const uid=localStorage.getItem("release-uid")||"fixture-A";if(expectedUid&&uid!==expectedUid)throw Error("Account changed");return ${process.env.ALUA_INTEGRATION_TEST?JSON.stringify(process.env.ALUA_RELEASE_INTEGRATION_TOKEN):"uid"}}
`);
    await file("src/features/auth/session.ts", `"use client";
import {useSyncExternalStore} from "react";
const initial={status:"loading" as const,user:null,profile:null,generation:0};
const states=new Map();const listeners=new Set<()=>void>();const signedOut={status:"signed_out",user:null,profile:null,generation:3};
function snapshot(){if(localStorage.getItem("release-signed-out"))return signedOut;const uid=localStorage.getItem("release-uid")||"fixture-A";if(!states.has(uid))states.set(uid,{status:"ready",user:{uid,email:"fixture@example.invalid"},profile:{uid,display_name:"Fixture"},generation:uid==="fixture-A"?1:2});return states.get(uid)}
export function useSession(){return useSyncExternalStore(listener=>{listeners.add(listener);return()=>{listeners.delete(listener)}},snapshot,()=>initial)}
export async function retrySession(){};export async function logout(){const {clearDraftOwner}=await import("@/features/reading/exam/draft-storage");await clearDraftOwner(localStorage.getItem("release-uid")||"fixture-A");localStorage.setItem("release-signed-out","1");listeners.forEach(fn=>fn())};export async function authenticate(..._args:unknown[]){};export function rejectSession(_generation:number){};
`);
  }
  await run(process.execPath, [require.resolve("next/dist/bin/next"), "build", "--webpack"], sandbox);
  await run(process.execPath, [join(dirname(require.resolve("@playwright/test/package.json")), "cli.js"), "test", process.env.ALUA_INTEGRATION_TEST?"--config=playwright.reading-integration.config.ts":process.env.ALUA_RELEASE_TEST?"--config=playwright.reading-release.config.ts":"--config=playwright.phase-c.config.ts", ...process.argv.slice(2)], root);
} catch (error) { console.error(error.message); process.exitCode = 1; }
finally { await rm(sandbox, { recursive: true, force: true }); }
