// Real Exam -> Finish -> Results -> Review on a disposable Next app and local API.
// The Python test owns the ephemeral PostgreSQL cluster. No API route mocks.
import {cp,mkdtemp,mkdir,readFile,rm,symlink,writeFile} from "node:fs/promises";
import {createRequire} from "node:module";
import {tmpdir} from "node:os";
import {dirname,join,resolve} from "node:path";
import {fileURLToPath} from "node:url";
import {spawn} from "node:child_process";

const web=resolve(dirname(fileURLToPath(import.meta.url)),".."),root=resolve(web,"..");
const require=createRequire(import.meta.url),{chromium,webkit,expect}=require("@playwright/test");
if(!process.env.ALUA_HOTFIX_TOKEN||!process.env.ALUA_HOTFIX_FIXTURE)throw Error("Run through the disposable backend pytest fixture.");
const fixtures=JSON.parse(await readFile(process.env.ALUA_HOTFIX_FIXTURE,"utf8"));
const sandbox=await mkdtemp(join(tmpdir(),"alua-reading-hotfix-"));
const output=join(root,"docs/reading-confirmed-defects-hotfix");await mkdir(output,{recursive:true});
const env={...process.env,NEXT_PUBLIC_API_BASE_URL:"http://127.0.0.1:3402/api/v1"};
for(const key of Object.keys(env))if(key.startsWith("NEXT_PUBLIC_FIREBASE"))env[key]="";
const results=[];let server,diagnosticPage,log="";
async function file(name,content){const p=join(sandbox,name);await mkdir(dirname(p),{recursive:true});await writeFile(p,content);}
try{
 for(const name of ["src","public","package.json","tsconfig.json","next.config.ts","postcss.config.mjs"])await cp(join(web,name),join(sandbox,name),{recursive:true});
 await symlink(join(web,"node_modules"),join(sandbox,"node_modules"),"dir");
 await file("src/lib/firebase/client.ts",`import type {Auth} from 'firebase/auth';export function firebaseConfigured(){return true}export async function getFirebaseAuth():Promise<Auth>{throw Error('Disposable fixture only')}export async function getIdToken(){return ${JSON.stringify(process.env.ALUA_HOTFIX_TOKEN)}}`);
 await file("src/features/auth/session.ts",`'use client';import {useSyncExternalStore} from 'react';const loading={status:'loading' as const,user:null,profile:null,generation:0};const ready={status:'ready' as const,user:{uid:'hotfix-fixture',email:'fixture@example.invalid'},profile:{uid:'hotfix-fixture',display_name:'Fixture'},generation:1};export function useSession(){return useSyncExternalStore(()=>()=>{},()=>ready,()=>loading)}export async function prepareGoogleAuth(){return async()=>{}}export async function retrySession(){}export async function logout(){}export async function authenticate(){}export function rejectSession(){}`);
 server=spawn(process.execPath,[require.resolve("next/dist/bin/next"),"dev","--webpack","--hostname","127.0.0.1","--port","3316"],{cwd:sandbox,env,stdio:["ignore","pipe","pipe"]});
 server.stdout.on("data",d=>{log+=d.toString()});server.stderr.on("data",d=>{log+=d.toString()});
 for(let n=0;n<100;n++){try{await fetch("http://127.0.0.1:3316");break}catch{}await new Promise(r=>setTimeout(r,300));if(n===99)throw Error(log.slice(-1500));}
 for(const [browserName,engine,viewport]of [["chromium",chromium,{width:1366,height:768}],["webkit",webkit,{width:390,height:844}]]){
  const browser=await engine.launch({headless:true});
  try{
   for(const [eid,fixture]of Object.entries(fixtures)){
    const context=await browser.newContext({viewport});const page=await context.newPage();diagnosticPage=page;page.setDefaultTimeout(20000);
    const errors=[],outside=[],assetRequests=[],submits=[];
    page.on("pageerror",e=>errors.push(e.message));page.on("request",request=>{const url=request.url();if(url.startsWith("blob:"))return;const host=new URL(url).hostname;if(!["localhost","127.0.0.1"].includes(host))outside.push(new URL(url).origin);if(url.includes("/reading/assets/"))assetRequests.push(url);if(url.endsWith("/submit"))submits.push(request.postDataJSON())});
    const book=Number(eid.split("-")[1]);await page.goto(`http://127.0.0.1:3316/reading/cambridge-${book}/${eid}`);
    const start=page.getByRole("button",{name:"Start test",exact:true});await expect(start).toBeEnabled({timeout:60000});
    const [createdResponse]=await Promise.all([page.waitForResponse(r=>r.request().method()==="POST"&&r.url().endsWith("/api/alua/reading/attempts")),start.click()]);const created=await createdResponse.json();
    await expect(page.getByRole("button",{name:"Finish",exact:true})).toBeVisible();
    const snapshotResponse=await page.request.get(`http://127.0.0.1:3402/api/v1/reading/attempts/${created.id}`,{headers:{Authorization:`Bearer ${process.env.ALUA_HOTFIX_TOKEN}`}});
    const snapshot=await snapshotResponse.json(),groups=snapshot.exam.passages.flatMap(p=>p.question_groups.map(g=>({...g,passage:p.number}))).filter(g=>fixture.groups.includes(g.id));
    const examined=[];
    for(const g of groups){
     await page.getByRole("button",{name:`Passage ${g.passage}`,exact:true}).click();if(viewport.width<700)await page.locator(".mobile-panels").getByRole("button",{name:"Questions",exact:true}).click();
     const section=page.getByRole("region",{name:`Questions for passage ${g.passage}`,exact:true});await expect(section).toBeVisible();
     expect(await page.locator(".passage-article").evaluate(article=>{const title=article.querySelector("h1")?.textContent.trim().toLowerCase();return [...article.querySelectorAll("h2")].filter(h=>h.textContent.trim().toLowerCase()===title).length})).toBe(0);
     for(const [index,q]of g.questions.entries()){
      const anchor=section.locator(`[data-question="${q.number}"]`);await expect(anchor).toBeVisible();const value=fixture.answers[q.id];
      if(q.answer_input_type==="text"){await anchor.getByRole("textbox").fill(value);}
      else if(q.type==="multiple_choice_single"){await anchor.locator(`input[type="radio"][value="${value}"]`).check();}
      else{
       const field=anchor.getByRole("group",{name:`Answer ${q.number}`,exact:true});
       if(index===0&&g.options.length>2){for(const option of g.options){const optionButton=field.getByRole("button",{name:option.label,exact:true});await expect(optionButton).toBeEnabled();await optionButton.click();await expect(optionButton).toHaveAttribute("aria-pressed","true");}}
       const chosen=field.getByRole("button",{name:value,exact:true});if(await chosen.getAttribute("aria-pressed")!=="true")await chosen.click();
      }
      examined.push(q.id);
     }
     if(g.representation==="structured_text"&&g.type==="summary_completion"){
      for(const q of g.questions)await expect(section.locator(`.inline-question[data-question="${q.number}"]`)).toHaveCount(1);
      const title=g.instructions.split("\n\n")[1];if(title&&title.length<100)expect((await section.innerText()).split(title).length-1).toBe(1);
      const taskText=await section.locator(`[data-question="${g.question_numbers[0]}"]`).evaluate(e=>e.closest(".question-group").innerText);
      expect(taskText.split(`Questions ${g.question_numbers[0]}–${g.question_numbers.at(-1)}`).length-1).toBe(1);
     }
     if(g.id.endsWith("g-14-20")){
      const im=section.locator(".reading-asset img").first();await expect(im).toBeVisible();await expect.poll(()=>im.evaluate(e=>e.naturalHeight)).toBeGreaterThan(1200);
      expect(g.assets[0].id).toContain("fidelity-v1");
     }
    }
    // Returning to a prepared source group must reuse its cached image.
    if(eid==="cambridge-07-test-01"){
     await page.getByRole("button",{name:"Passage 2",exact:true}).click();await page.waitForTimeout(150);const before=assetRequests.length;
     await page.getByRole("button",{name:"Passage 1",exact:true}).click();await page.getByRole("button",{name:"Passage 2",exact:true}).click();await page.waitForTimeout(150);expect(assetRequests.length).toBe(before);
    }
    await expect(page.locator(".save-status")).toHaveText("All changes saved");
    await page.getByRole("button",{name:"Finish",exact:true}).click();const submitResponse=page.waitForResponse(r=>r.url().endsWith(`/reading/attempts/${created.id}/submit`));await page.getByRole("button",{name:"Finish test",exact:true}).click();
    const response=await submitResponse,terminal=await response.json();expect(response.status()).toBe(200);expect(terminal.final_snapshot_accepted).toBe(true);expect(submits.length).toBe(1);expect(Object.keys(submits[0].answers)).toHaveLength(40);
    for(const qid of examined){expect(terminal.answers[qid]).toBe(fixture.answers[qid]);expect(terminal.result.positions.find(p=>p.question_id===qid).is_correct).toBe(true);}
    await expect(page.getByRole("region",{name:"Test result"})).toBeVisible();await page.getByRole("link",{name:/^Review test/}).click();await expect(page.locator(".exam-workspace")).toBeVisible();
    for(const g of groups){
     await page.getByRole("button",{name:`Passage ${g.passage}`,exact:true}).click();if(viewport.width<700)await page.locator(".mobile-panels").getByRole("button",{name:"Questions",exact:true}).click();
     for(const q of g.questions){const anchor=page.getByRole("region",{name:`Questions for passage ${g.passage}`,exact:true}).locator(`[data-question="${q.number}"]`);await expect(anchor).toBeVisible();expect(await anchor.locator("input:not(:disabled),button[aria-pressed]:not(:disabled)").count()).toBe(0);await expect(anchor).toContainText("Correct answer:");}
    }
    expect(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)).toBe(false);expect(outside).toEqual([]);expect(errors).toEqual([]);
    await page.screenshot({path:join(output,`${eid}-${browserName}-review.png`)});
    results.push({exam_id:eid,content_hash:created.content_hash,browser:browserName,viewport,question_groups:groups.map(g=>g.id),questions_checked:examined,restored_bank_options_selectable:true,inline_blanks_present:true,finish_atomic_snapshot_accepted:true,submitted_answers_match:true,affected_answers_grade_correct:true,review_read_only:true,asset_requests:assetRequests.length,errors});
    console.log(`Hotfix ${browserName}: ${eid} Exam/Finish/Review PASS (${examined.length} questions)`);await context.close();
   }
  }finally{await browser.close();}
 }
 await writeFile(join(output,"browser-qa.json"),JSON.stringify({scope:"Six affected tests only; real local API and disposable PostgreSQL; no API route mocks",results},null,2)+"\n");
}catch(error){let body="";try{body=await diagnosticPage?.locator("body").innerText();await diagnosticPage?.screenshot({path:join(output,"browser-failure.png")});}catch{}await writeFile(join(output,"browser-failure.txt"),String(error)+"\n"+body+"\n"+log.slice(-6000));throw error;}
finally{if(server){server.kill("SIGTERM");await new Promise(r=>{server.once("exit",r);setTimeout(r,3000)})}await rm(sandbox,{recursive:true,force:true});}
