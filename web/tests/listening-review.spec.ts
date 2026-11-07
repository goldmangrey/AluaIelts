import {test,expect,type Page} from '@playwright/test';
import {execFileSync} from 'node:child_process';
import {readFileSync} from 'node:fs';
import {resolve} from 'node:path';
import type {Entry,Exam,Result} from '../src/features/listening/models';
// Use the existing pure grader and original dataset unchanged. No database is used.
const fixtures:Record<string,Result>=JSON.parse(execFileSync(resolve('../backend/.venv/bin/python'),['-c',`
import json
from pathlib import Path
from app.modules.listening.grading import result_for, forms
root=Path('app/content/listening_v1')
results={}
for mode,eid in [('verified','cambridge-14-test-01'),('preliminary','cambridge-06-test-01'),('ungraded','cambridge-04-test-02'),('practice','cambridge-21-test-02')]:
 exam=json.loads((root/'exams'/f'{eid}.json').read_text())
 key=json.loads((root/'keys'/f'{eid}.json').read_text())
 answers={}
 for k in key['answers'][:8]:
  try:answers[k['question_id']]=k['explicit_slash_forms'][0] if '(' not in k['explicit_slash_forms'][0] else min(forms(k['official_answer']),key=lambda v:(len(v.split()),len(v)))
  except ValueError:pass
 answers[eid+'-q02']='deliberately incorrect'
 answers.pop(eid+'-q03',None)
 if mode=='preliminary':answers[eid+'-q07']='10am'
 if mode=='ungraded':answers[eid+'-q01']='B'
 if mode=='practice':answers[eid+'-q12']='wrong'
 data=result_for({'exam':exam,'key':key,'mode':'ungraded' if mode=='practice' else mode,**({'grading_policy':'practice-v2'} if mode=='practice' else {})},answers)
 data.update(attempt_id='00000000-0000-4000-8000-000000000001',exam=exam)
 results[mode]=data
print(json.dumps(results))
`],{cwd:resolve('../backend'),env:{...process.env,PYTHONDONTWRITEBYTECODE:'1'},encoding:'utf8'}));
const baseline=process.env.ALUA_REVIEW_BASELINE==='1';
test.beforeEach(async({page})=>{await page.route('**/*',route=>(route.request().url().startsWith('blob:')||['127.0.0.1','localhost'].includes(new URL(route.request().url()).hostname))?route.continue():route.abort());});
async function load(page:Page,mode='verified'){
 const result=fixtures[mode]!;const exam=result.exam!;
 const mutations:string[]=[];
 await page.route('**/api/alua/**',route=>{
  const request=route.request();if(request.method()!=='GET'){mutations.push(request.url());return route.fulfill({status:405});}
  const assetId=request.url().split('/assets/')[1];
  if(assetId){const asset=exam.assets.find(a=>a.asset_id===assetId)!;return route.fulfill({status:200,contentType:asset.relative_path.endsWith('.png')?'image/png':'image/jpeg',body:readFileSync(resolve('../backend/app/content/listening_v1',asset.relative_path))});}
  return route.fulfill({status:200,json:result});
 });
 await page.route('**/api/listening/authorize',route=>route.fulfill({status:200,json:{}}));
 // Tiny local PCM WAV, supported by both engines; no real recordings are changed.
 const samples=8000*12,wav=Buffer.alloc(44+samples*2);wav.write('RIFF');wav.writeUInt32LE(wav.length-8,4);wav.write('WAVEfmt ',8);wav.writeUInt32LE(16,16);wav.writeUInt16LE(1,20);wav.writeUInt16LE(1,22);wav.writeUInt32LE(8000,24);wav.writeUInt32LE(16000,28);wav.writeUInt16LE(2,32);wav.writeUInt16LE(16,34);wav.write('data',36);wav.writeUInt32LE(samples*2,40);
 await page.route('**/api/listening/audio/**',route=>{
  const range=/^bytes=(\d+)-(\d*)$/.exec(route.request().headers().range||'');
  if(range){const start=Number(range[1]),end=Math.min(wav.length-1,range[2]?Number(range[2]):wav.length-1);return route.fulfill({status:206,contentType:'audio/wav',headers:{'Accept-Ranges':'bytes','Content-Range':`bytes ${start}-${end}/${wav.length}`,'Content-Length':String(end-start+1)},body:wav.subarray(start,end+1)});}
  return route.fulfill({status:200,contentType:'audio/wav',headers:{'Accept-Ranges':'bytes','Content-Length':String(wav.length)},body:wav});
 });
 await page.goto(`/listening/attempts/${result.attempt_id}/review`);
 await expect(page.getByRole('heading',{name:'Review your answers'})).toBeVisible();
 return {result,mutations};
}
async function sourceTab(page:Page){const tab=page.getByRole('button',{name:'Source material',exact:true});if(await tab.isVisible())await tab.click();}
async function questionsTab(page:Page){const tab=page.getByRole('button',{name:'Questions',exact:true});if(await tab.isVisible())await tab.click();}
async function go(page:Page,n:number){await page.getByRole('button',{name:'Question navigator',exact:true}).click();await page.getByRole('button',{name:`Go to question ${n}`,exact:true}).click();}

test('Review screenshots and viewport',async({page},info)=>{
 await load(page);
 if(baseline){await page.screenshot({path:`docs/listening-review-v2/before/${info.project.name}.png`,fullPage:true});return;}
 const source=page.getByRole('region',{name:'Listening source material',includeHidden:true});
 const questions=page.getByRole('region',{name:'Listening questions',exact:true});
 await sourceTab(page);await expect.poll(()=>source.locator('img').first().evaluate(el=>(el as HTMLImageElement).naturalWidth)).toBeGreaterThan(0);
 const original=fixtures.verified!.exam!.assets.find(a=>a.asset_id===fixtures.verified!.exam!.parts[0]!.supporting_assets[0])!;
 const rendered=source.locator(`[data-source-asset="${original.asset_id}"] img`).first();
 expect(await rendered.evaluate(async el=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',await(await fetch((el as HTMLImageElement).src)).arrayBuffer()))).map(n=>n.toString(16).padStart(2,'0')).join(''))).toBe(original.asset_id.slice(6));
 await page.screenshot({path:`docs/listening-review-v2/after/${info.project.name}-source.png`});
 await source.getByRole('button',{name:'Enlarge source image'}).first().click();await expect(page.getByRole('button',{name:'Close image'})).toBeVisible();await page.keyboard.press('Escape');
 await questionsTab(page);await expect(questions).toBeVisible();
 await expect(page.locator('#question-1')).toHaveAttribute('data-review-status','correct');await expect(page.locator('#question-2')).toHaveAttribute('data-review-status','incorrect');await expect(page.locator('#question-3')).toHaveAttribute('data-review-status','unanswered');
 await expect(page.locator('#question-2')).toContainText('furniture');
 await page.screenshot({path:`docs/listening-review-v2/after/${info.project.name}-questions.png`});
 expect(await page.evaluate(()=>document.documentElement.scrollHeight<=innerHeight+1&&document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 const footer=(await page.locator('footer').boundingBox())!,panel=(await questions.boundingBox())!;expect(panel.y+panel.height).toBeLessThanOrEqual(footer.y+1);
});

test('Verified navigation, filters, divider, scroll and read-only playback',async({page},info)=>{
 test.skip(baseline);
 const {result,mutations}=await load(page);
 const source=page.getByRole('region',{name:'Listening source material',includeHidden:true});
 const questions=page.getByRole('region',{name:'Listening questions',exact:true});
 const divider=page.getByRole('separator',{name:'Resize Listening panels'});
 if(await divider.isVisible()){
  await expect(divider).toHaveAttribute('aria-valuenow','55');
  const rect=(await divider.boundingBox())!;await page.mouse.move(rect.x+7,rect.y+80);await page.mouse.down();await page.mouse.move(page.viewportSize()!.width*.4,rect.y+80);await page.mouse.up();await expect(divider).toHaveAttribute('aria-valuenow','40');
  await divider.focus();await page.keyboard.press('ArrowRight');await expect(divider).toHaveAttribute('aria-valuenow','42');await divider.dblclick();await expect(divider).toHaveAttribute('aria-valuenow','55');
  await source.evaluate(el=>{el.scrollTop=140;});const offset=await source.evaluate(el=>el.scrollTop);
  await questions.evaluate(el=>{el.scrollTop=300;});expect(await questions.evaluate(el=>el.scrollTop)).toBeGreaterThan(0);expect(await source.evaluate(el=>el.scrollTop)).toBe(offset);
 }
 await expect(page.getByText('Estimated Band',{exact:true})).toBeVisible();
 await expect(page.getByRole('region',{name:'Listening audio player'})).toHaveCount(1);
 await expect(page.getByRole('region',{name:'Listening audio player'})).toBeVisible();
 await expect.poll(()=>page.locator('audio').first().evaluate(el=>(el as HTMLAudioElement).readyState)).toBeGreaterThan(0);
 await page.getByRole('button',{name:'Play',exact:true}).click();await expect.poll(()=>page.locator('audio').first().evaluate(el=>(el as HTMLAudioElement).currentTime)).toBeGreaterThan(.1);
 await page.getByRole('button',{name:'Pause',exact:true}).click();await page.getByLabel('Audio progress').fill('6');
 await page.getByLabel('Audio progress').fill('0');await expect.poll(()=>page.locator('audio').first().evaluate(el=>(el as HTMLAudioElement).readyState)).toBeGreaterThan(0);expect(await page.locator('audio').first().evaluate(el=>(el as HTMLAudioElement).currentTime)).toBeLessThan(.5);
 await page.getByRole('button',{name:/^Part 3/}).click();await page.getByRole('button',{name:'Listen to Part 3',exact:true}).click();await expect(page.locator('audio').first()).toHaveAttribute('src',/\/3$/);
 await page.getByRole('button',{name:/^Part 1/}).click();
 await page.getByRole('button',{name:/^Incorrect/}).click();await questionsTab(page);
 await expect(questions.locator('[id^=question-]')).toHaveCount(result.questions.filter(q=>q.part_number===1&&q.correct===false&&q.user_answer.trim()).length);await expect(page.locator('#question-2')).toBeInViewport();
 await page.getByRole('button',{name:/^Unanswered/}).click();await expect(page.locator('#question-3')).toBeInViewport();
 await page.getByRole('button',{name:'All',exact:true}).click();
 await page.getByRole('button',{name:'Question navigator',exact:true}).click();
 const grid=page.getByRole('navigation',{name:'Questions',exact:true});await expect(grid.getByRole('button')).toHaveCount(40);
 for(const [n,status] of [[1,'correct'],[2,'incorrect'],[3,'unanswered']] as const)await expect(grid.getByRole('button',{name:`Go to question ${n}`,exact:true})).toHaveAttribute('data-review-status',status);
 await page.screenshot({path:`docs/listening-review-v2/after/${info.project.name}-navigator.png`});
 await page.keyboard.press('Escape');await expect(grid).toBeHidden();
 await go(page,11);await expect(page.locator('#question-11')).toBeInViewport();await sourceTab(page);await questionsTab(page);await expect(page.getByRole('region',{name:'Answer bank'}).first()).toBeVisible();
 await questionsTab(page);await questions.dispatchEvent('wheel',{deltaY:1000});await questions.evaluate(el=>{const next=el.querySelectorAll('[data-question-group]')[1]!;el.scrollTop+=next.getBoundingClientRect().top-el.getBoundingClientRect().top-20;});await expect(source.locator('header span')).toHaveCount(0);await go(page,40);await expect(page.locator('#question-40')).toBeInViewport();await expect(grid).toBeHidden();
 await page.getByRole('button',{name:'Previous question',exact:true}).click();await expect(page.locator('#question-39')).toBeInViewport();
 await page.getByRole('button',{name:'Next question',exact:true}).click();await expect(page.locator('#question-40')).toBeInViewport();
 await page.reload();await expect(page.locator('#question-1')).toContainText(result.questions[0]!.user_answer);
 await expect(page.locator('main input:not([type=range]),main select:not(#review-audio-part),main textarea')).toHaveCount(0);
 await expect(page.getByRole('button',{name:/Finish|Submit|Mark question/})).toHaveCount(0);
 expect(mutations).toEqual([]);
 expect(await page.evaluate(()=>document.documentElement.scrollHeight<=innerHeight+1&&document.documentElement.scrollWidth<=innerWidth)).toBe(true);
});

for(const mode of ['preliminary','ungraded'])test(`${mode}: honest statuses and corrections`,async({page},info)=>{
 test.skip(baseline);
 const {mutations,result}=await load(page,mode);
 await questionsTab(page);
 await expect(page.getByText('Estimated Band',{exact:true})).toHaveCount(0);
 if(mode==='preliminary'){
  await expect(page.locator('#question-1')).toHaveAttribute('data-review-status','correct');
  await expect(page.locator('#question-2')).toHaveAttribute('data-review-status','incorrect');
  await go(page,7);await expect(page.locator('#question-7')).toHaveAttribute('data-review-status','ungraded');await expect(page.locator('#question-7')).toContainText('No reliable correction available');
  // The backend may retain ambiguous official notation; it is never a correction.
  await expect(page.locator('#question-7')).not.toContainText(result.questions.find(q=>q.question_number===7)!.correct_answer!);
  await page.getByRole('button',{name:/^Incorrect/}).click();await expect(page.getByRole('region',{name:'Listening questions',exact:true}).locator('[data-review-status=ungraded]')).toHaveCount(0);
 }else{
  await expect(page.locator('#question-1')).toHaveAttribute('data-review-status','ungraded');
  await expect(page.locator('main [data-review-status=correct],main [data-review-status=incorrect]')).toHaveCount(0);
  await expect(page.getByRole('button',{name:/^Incorrect/})).toHaveCount(0);
  await expect(page.locator('#question-1')).toContainText('no reliable official answer key');
 }
 await page.getByRole('button',{name:'All',exact:true}).click();await go(page,3);await expect(page.locator('#question-3')).toHaveAttribute('data-review-status','unanswered');
 await page.screenshot({path:`docs/listening-review-v2/after/${info.project.name}-${mode}.png`});
 await page.getByRole('button',{name:'Question navigator',exact:true}).click();const grid=page.getByRole('navigation',{name:'Questions',exact:true});await expect(grid.getByRole('button')).toHaveCount(40);
 if(mode==='ungraded')await expect(grid.locator('[data-review-status=correct],[data-review-status=incorrect]')).toHaveCount(0);
 expect(mutations).toEqual([]);
});

test('Shared V3 workspace still edits and navigates without marking',async({page})=>{
 test.skip(baseline);
 const result=fixtures.verified!,exam:Exam=result.exam!,id=result.attempt_id;
 const snapshot={id,exam_id:exam.exam_id,status:'in_progress',version:1,mode:'verified',content_hash:'review-ui-regression-only',answers:{},state:{displayed_part:1,current_question:1,audio_part:1,playback_seconds:0,marked:[]},exam};
 let saves=0;
 await page.route('**/api/alua/**',route=>{
  const req=route.request();const assetId=req.url().split('/assets/')[1];if(assetId){const asset=exam.assets.find(a=>a.asset_id===assetId)!;return route.fulfill({status:200,contentType:asset.relative_path.endsWith('.png')?'image/png':'image/jpeg',body:readFileSync(resolve('../backend/app/content/listening_v1',asset.relative_path))});}
  if(req.url().endsWith('/sync')){const body=req.postDataJSON();snapshot.answers=body.answers;snapshot.state=body.state;snapshot.version++;saves++;}
  return route.fulfill({status:200,json:snapshot});
 });
 await page.route('**/api/listening/authorize',route=>route.fulfill({status:200,json:{}}));await page.route('**/api/listening/audio/**',route=>route.fulfill({status:404}));
 await page.goto(`/listening/attempts/${id}`);await questionsTab(page);
 await page.getByLabel('Question 1',{exact:true}).fill('Canadian');await expect(page.getByRole('button',{name:/^(Unmark|Mark) question/})).toHaveCount(0);
 await page.getByRole('button',{name:'Question navigator',exact:true}).click();const grid=page.getByRole('navigation',{name:'Questions',exact:true});
 await expect(grid.getByRole('button',{name:'Go to question 1',exact:true})).toHaveAttribute('data-answered','true');await expect(grid.locator('[data-marked]')).toHaveCount(0);
 await grid.getByRole('button',{name:'Go to question 40',exact:true}).click();await expect(page.locator('#question-40')).toBeInViewport();await expect(page.getByRole('button',{name:'Finish practice',exact:true})).toBeVisible();
 await expect.poll(()=>saves).toBeGreaterThan(0);
 expect(await page.evaluate(()=>document.documentElement.scrollHeight<=innerHeight+1&&document.documentElement.scrollWidth<=innerWidth)).toBe(true);
});

test('Short mobile viewport keeps audio, navigator and panels reachable',async({page},info)=>{
 test.skip(baseline||!info.project.name.endsWith('mobile'));
 await page.setViewportSize({width:375,height:667});await load(page);
 await page.getByRole('button',{name:'Question navigator',exact:true}).click();
 const viewport=page.viewportSize()!;
 const footer=(await page.locator('footer').boundingBox())!;
 expect(footer.y+footer.height).toBeLessThanOrEqual(viewport.height+1);
 await page.getByRole('button',{name:'Go to question 40',exact:true}).click();await expect(page.locator('#question-40')).toBeInViewport();
 await page.getByRole('button',{name:/^Hide audio/}).click();
 expect(await page.evaluate(()=>document.documentElement.scrollHeight<=innerHeight+1&&document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await page.screenshot({path:`docs/listening-review-v2/after/${info.project.name}-short.png`});
});


test('Catalog hides all metadata labels and preserves genuine launch failures',async({page})=>{
 const entries:Entry[]=JSON.parse(execFileSync(resolve('../backend/.venv/bin/python'),['-c',
  'import json; from app.modules.listening.catalog import ListeningCatalog; c=ListeningCatalog(); print(json.dumps([c.entry(e) for e in c.exams]))'],
  {cwd:resolve('../backend'),env:{...process.env,PYTHONDONTWRITEBYTECODE:'1'},encoding:'utf8'}));
 const modes=['verified','preliminary','ungraded','blocked'] as const;
 for(let i=0;i<4;i++){entries[i]!.content_mode=modes[i]!;entries[i]!.can_start=i!==3;entries[i]!.block_reason=i===3?'Some original question positions are incomplete.':null;}
 await page.route('**/api/alua/listening/exams',route=>route.fulfill({status:200,json:{items:entries}}));
 await page.route('**/api/alua/listening/exams/*',route=>route.fulfill({status:200,json:{exam:fixtures.verified!.exam,metadata:entries[3]}}));
 await page.goto('/listening');await expect(page.locator('main a[href*="cambridge-"]')).toHaveCount(72);
 for(let i=0;i<4;i++){
  const entry=entries[i]!,card=page.locator(`main a[href="/listening/${entry.book}/${entry.exam_id}"]`);
  await expect(card.locator('[data-mode]')).toHaveCount(0);
  await expect(card).not.toContainText(/Verified|Preliminary|Ungraded|Unavailable/);
 }
 const blocked=entries[3]!;await page.locator(`main a[href="/listening/${blocked.book}/${blocked.exam_id}"]`).click();
 await expect(page.getByRole('button',{name:'Start Listening',exact:true})).toBeDisabled();
 await expect(page.getByRole('status')).toContainText('Some original question positions are incomplete.');
});


test('Practice scoring and review use verdicts regardless of editorial metadata',async({page})=>{
 const {result,mutations}=await load(page,'practice');
 expect(result.mode).toBe('ungraded');expect(result.graded_count).toBe(40);expect(result.estimated_band).not.toBeNull();
 await questionsTab(page);
 await expect(page.locator('#question-1')).toHaveAttribute('data-review-status','correct');
 await expect(page.locator('#question-2')).toHaveAttribute('data-review-status','incorrect');
 await go(page,3);await expect(page.locator('#question-3')).toHaveAttribute('data-review-status','unanswered');await expect(page.locator('#question-3')).toContainText('Correct answer');
 await expect(page.locator('main')).not.toContainText(/Verified|Preliminary|Ungraded|preliminary key/);
 await page.getByRole('link',{name:'← Results',exact:true}).click();
 await expect(page.getByText('Estimated practice band',{exact:true})).toBeVisible();
 await expect(page.getByText(`${result.correct_count} / 40`,{exact:true})).toBeVisible();
 await expect(page.locator('main')).not.toContainText(/Verified|Preliminary|Ungraded|preliminary key/);
 expect(mutations).toEqual([]);
});


const explanation=(number:number)=>({what_happened:'В записи сначала упоминают другой вариант, затем называют окончательный ответ.',why:'Сохранённый ответ не совпадает с подтверждённой фразой.',next_time:'Дослушайте уточнение до конца.',evidence:{available:true,reason:null,part:Math.ceil(number/10),quote:'A real supplied fixture segment.',segment_ids:['seg-0001'],clip_start:number===12?11.4:.6,clip_end:number===12?12:1.2}});
test('AI review is click-only, cached, collapsible and uses one player for moments and loops',async({page},info)=>{
 let calls=0;await page.route('**/api/listening/review',route=>{calls++;const body=route.request().postDataJSON();expect(Object.keys(body).sort()).toEqual(['attempt_id','question_number']);return route.fulfill({status:200,json:explanation(body.question_number)});});
 const {mutations}=await load(page,'practice');await questionsTab(page);expect(calls).toBe(0);
 await expect(page.locator('#question-1').getByRole('button',{name:'Explain with AI'})).toHaveCount(0);
 await expect(page.locator('#question-3').getByRole('button',{name:'Explain with AI'})).toHaveCount(0);
 await go(page,2);await page.locator('#question-2').getByRole('button',{name:'Explain with AI'}).click();
 const panel=page.getByRole('region',{name:'AI explanation for question 2'});await expect(panel).toContainText('Дослушайте уточнение');expect(calls).toBe(1);
 await panel.getByRole('button',{name:'Play Moment',exact:true}).click();
 await expect(page.locator('audio').first()).toHaveAttribute('src',/\/1$/);
 await expect.poll(()=>page.locator('audio').first().evaluate(el=>(el as HTMLAudioElement).currentTime)).toBeGreaterThan(.6);
 await expect.poll(()=>page.locator('audio').first().evaluate(el=>(el as HTMLAudioElement).paused)).toBe(true);
 expect(await page.locator('audio').first().evaluate(el=>(el as HTMLAudioElement).currentTime)).toBeCloseTo(0,1);
 await panel.getByRole('button',{name:'Loop Moment',exact:true}).click();
 await expect(panel.getByRole('button',{name:'Loop Moment'})).toHaveAttribute('aria-pressed','true');
 await page.locator('audio').first().evaluate(el=>{el.setAttribute('data-loop-seeks','0');el.addEventListener('seeked',()=>{if((el as HTMLAudioElement).currentTime<.8)el.setAttribute('data-loop-seeks',String(Number(el.getAttribute('data-loop-seeks'))+1));});});
 await expect.poll(()=>page.locator('audio').first().getAttribute('data-loop-seeks')).toMatch(/^[2-9]/);
 expect(await page.locator('audio').evaluateAll(els=>els.filter(el=>!(el as HTMLAudioElement).paused).length)).toBe(1);
 await page.screenshot({path:`docs/listening-review-v2/ai/${info.project.name}.png`});
 await panel.getByRole('button',{name:'Loop Moment',exact:true}).click();await expect.poll(()=>page.locator('audio').first().evaluate(el=>(el as HTMLAudioElement).paused)).toBe(true);
 await page.locator('#question-2').getByRole('button',{name:'Explain with AI'}).click();await expect(panel).toHaveCount(0);
 await page.locator('#question-2').getByRole('button',{name:'Explain with AI'}).click();await expect(panel).toBeVisible();expect(calls).toBe(1);
 await go(page,12);await expect(panel).toHaveCount(0);await page.locator('#question-12').getByRole('button',{name:'Explain with AI'}).click();
 const second=page.getByRole('region',{name:'AI explanation for question 12'});await second.getByRole('button',{name:'Loop Moment'}).click();await expect(page.locator('audio').first()).toHaveAttribute('src',/\/2$/);
 await expect.poll(()=>page.locator('audio').first().evaluate(el=>(el as HTMLAudioElement).paused)).toBe(false);
 await page.locator('audio').first().evaluate(el=>{el.setAttribute('data-end-loops','0');el.addEventListener('seeked',()=>{if((el as HTMLAudioElement).currentTime>11.3&&(el as HTMLAudioElement).currentTime<11.6)el.setAttribute('data-end-loops',String(Number(el.getAttribute('data-end-loops'))+1));});});
 await expect.poll(()=>page.locator('audio').first().getAttribute('data-end-loops')).toMatch(/^[2-9]/);
 await expect(page.locator('audio').first()).toHaveAttribute('src',/\/2$/);
 await go(page,1);await expect(second).toHaveCount(0);await expect.poll(()=>page.locator('audio').first().evaluate(el=>(el as HTMLAudioElement).paused)).toBe(true);
 await go(page,2);await page.locator('#question-2').getByRole('button',{name:'Explain with AI'}).click();await panel.getByRole('button',{name:'Loop Moment'}).click();
 await page.getByRole('link',{name:'← Results',exact:true}).click();await expect(page.locator('audio')).toHaveCount(0);
 expect(mutations).toEqual([]);
});

test('AI retry, incomplete evidence, reload and normal playback stay usable',async({page})=>{
 let calls=0,available=true;
 await page.route('**/api/listening/review',route=>{calls++;return calls===1?route.fulfill({status:503,json:{}}):route.fulfill({status:200,json:available?explanation(2):{...explanation(2),evidence:{available:false,reason:'transcript_incomplete',part:1,quote:null,segment_ids:[],clip_start:null,clip_end:null}}});});
 await load(page,'practice');await questionsTab(page);await go(page,2);await page.locator('#question-2').getByRole('button',{name:'Explain with AI'}).click();
 const panel=page.getByRole('region',{name:'AI explanation for question 2'});await panel.getByRole('button',{name:'Retry',exact:true}).click();await expect(panel).toContainText('Дослушайте уточнение');expect(calls).toBe(2);
 await page.reload();await questionsTab(page);await go(page,2);available=false;await page.locator('#question-2').getByRole('button',{name:'Explain with AI'}).click();await expect(panel).toContainText('Дослушайте уточнение');
 await expect(panel.getByRole('button',{name:'Play Moment'})).toHaveCount(0);await expect(panel.getByRole('button',{name:'Loop Moment'})).toHaveCount(0);
 await expect.poll(()=>page.locator('audio').first().evaluate(el=>(el as HTMLAudioElement).readyState)).toBeGreaterThan(0);
 await page.getByRole('button',{name:'Play',exact:true}).click();await page.getByLabel('Audio progress').fill('4');await page.getByRole('button',{name:'Pause',exact:true}).click();
 expect(await page.locator('audio').first().evaluate(el=>(el as HTMLAudioElement).currentTime)).toBeGreaterThanOrEqual(4);
});
