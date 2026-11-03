// Disposable synthetic passage + mocked Firebase transport. Never included in deployment.
import { mkdtemp, cp, symlink, rm, mkdir, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { spawn } from "node:child_process";
const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const temporary = await mkdtemp(join(tmpdir(), "alua-translate-"));
try {
  for (const name of ["src", "package.json", "tsconfig.json", "next.config.ts", "postcss.config.mjs"])
    await cp(join(root, name), join(temporary, name), { recursive: true });
  await symlink(join(root, "node_modules"), join(temporary, "node_modules"));
  await writeFile(join(temporary, "src/lib/firebase/client.ts"), 'export async function getIdToken(){return "mock.firebase.signature"}; export async function getFirebaseAuth(){throw Error("Test only")}; export function firebaseConfigured(){return false};');
  await mkdir(join(temporary, "src/app/translate-qa"), { recursive: true });
  await writeFile(join(temporary, "src/app/translate-qa/page.tsx"), `"use client";
import {useEffect,useState} from "react";
import {PassagePane} from "@/features/reading/exam/passage-pane";
export default function Page(){const [ready,setReady]=useState(false);useEffect(()=>setReady(true),[]);return <main data-ready={ready} style={{padding:24,maxWidth:700}}><PassagePane passage={{id:"p1",number:1,title:"Translation fixture",subtitle:null,question_groups:[],question_numbers:[],content:[{type:"paragraph",label:null,text:"She is looking forward to studying abroad. I used to walk to school. I am used to walking. We take into account every detail. The evidence is compelling."}]}} size={18} translation={{uid:"fixture",attemptId:"11111111-2222-4333-8444-555555555555"}}/><input aria-label="Answer"/><div style={{height:1600}}/></main>}`);
  const code = await new Promise((ok, fail) => {
    const child = spawn("pnpm", ["exec", "playwright", "test", "--config=playwright.translate.config.ts", ...process.argv.slice(2)], { cwd: root, env: { ...process.env, ALUA_TRANSLATE_APP: temporary }, stdio: "inherit" });
    child.on("error", fail); child.on("exit", ok);
  });
  process.exitCode = code ?? 1;
} finally { await rm(temporary, { recursive: true, force: true }); }
