import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import type { Page } from "@playwright/test";
export const fixture = JSON.parse(execFileSync(resolve("../backend/.venv/bin/python"), ["-c", `
import json
from pathlib import Path
from app.modules.listening.grading import result_for as listen, forms
from app.modules.reading.grading import result_for as read
from app.modules.reading.catalog import ReadingCatalog
root=Path('app/content/listening_v1')
eid='cambridge-14-test-01'
exam=json.loads((root/'exams'/f'{eid}.json').read_text())
key=json.loads((root/'keys'/f'{eid}.json').read_text())
answers={k['question_id']:min(forms(k['official_answer']),key=len) for k in key['answers'][:8]}
answers[eid+'-q02']='wrong'
answers.pop(eid+'-q03',None)
l=listen({'exam':exam,'key':key,'mode':'verified'},answers)
l['exam']=exam
catalog=ReadingCatalog()
eid='cambridge-18-test-01'
snapshot={'exam':catalog.exams[eid],'key':catalog.keys[eid],'metadata':catalog.entries[eid]}
qs=[q for p in snapshot['exam']['passages'] for g in p['question_groups'] for q in g['questions']]
answers={qs[0]['id']:snapshot['key']['answers'][0]['canonical_answer'],qs[1]['id']:'wrong'}
r=read(snapshot,answers,'full_exam',None,120,{})
r['completion_reason']='submitted'
print(json.dumps({'listening':l,'reading':r,'readingExam':catalog.public_exam(snapshot['exam']),'answers':answers,'assets':{aid:str(catalog.path(a['path'])) for aid,a in catalog.assets.items()}}))
`], { cwd: resolve("../backend"), encoding: "utf8" }));
export const attemptId = "11111111-2222-4333-8444-555555555555";
export async function loadReview(page: Page, section: "listening"|"reading") {
  const assets: string[] = [], mutations: string[] = [];
  const result = {...fixture[section],attempt_id:attemptId};
  const exam = section==="reading"?fixture.readingExam:result.exam;
  await page.route("**/api/alua/**", async route => {
    const request=route.request(),path=new URL(request.url()).pathname;
    if(request.method()!=="GET"){mutations.push(path);await route.fulfill({status:405});return;}
    if(path.includes("/assets/")){
      const id=decodeURIComponent(path.split("/assets/")[1]!);assets.push(id);
      const asset=section==="listening"?exam.assets.find((a:{asset_id:string})=>a.asset_id===id):null;
      const file=asset?resolve("../backend/app/content/listening_v1",asset.relative_path):fixture.assets[id];
      await route.fulfill({body:readFileSync(file),contentType:asset?.relative_path.endsWith(".jpg")?"image/jpeg":"image/png"});return;
    }
    if(path.endsWith("/result")||path.endsWith("/review")){await route.fulfill({json:result});return;}
    if(path.endsWith("/books")){await route.fulfill({json:{items:[]}});return;}
    await route.fulfill({json:{id:attemptId,exam_id:exam.id,content_hash:result.content_hash,status:"submitted",mode:"full_exam",version:1,server_now:new Date().toISOString(),deadline_at:new Date(Date.now()+3600000).toISOString(),answers:fixture.answers,state:{current_passage:1,checked_question_ids:[]},not_fully_proofread:true,exam}});
  });
  await page.route("**/api/listening/authorize",route=>route.fulfill({json:{}}));
  const samples=8000*12,wav=Buffer.alloc(44+samples*2);wav.write("RIFF");wav.writeUInt32LE(wav.length-8,4);wav.write("WAVEfmt ",8);wav.writeUInt32LE(16,16);wav.writeUInt16LE(1,20);wav.writeUInt16LE(1,22);wav.writeUInt32LE(8000,24);wav.writeUInt32LE(16000,28);wav.writeUInt16LE(2,32);wav.writeUInt16LE(16,34);wav.write("data",36);wav.writeUInt32LE(samples*2,40);
  await page.route("**/api/listening/audio/**",route=>route.fulfill({contentType:"audio/wav",body:wav,headers:{"Accept-Ranges":"bytes"}}));
  await page.route("**/api/listening/review",route=>route.fulfill({json:{what_happened:"Your answer differs from the source.",why:"Listen for the speaker’s correction.",next_time:"Check the final detail.",evidence:{available:true,reason:null,part:1,quote:"The final detail",segment_ids:[],clip_start:1,clip_end:2}}}));
  await page.goto(`/${section}/attempts/${attemptId}/review`);
  await page.locator(section==="listening"?'[aria-label="Listening audio player"]':'.exam-workspace').waitFor();
  return { assets, mutations };
}
