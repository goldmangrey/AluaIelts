import {expectCenteredDialog,expectNoSaveIndicators,watchSaveIndicators} from "./exam-ui-assertions";
import {readFileSync} from "node:fs";
import {resolve} from "node:path";
import {displayedPart,sourceMaterial} from "../src/features/listening/source-material";
import type {Exam,Attempt} from "../src/features/listening/models";
import {test,expect} from "@playwright/test";
import visualPolicy from "../src/features/listening/visual-materials.json";
test.setTimeout(90000);
test.beforeEach(async({page})=>{await page.route("**/*",route=>{const url=new URL(route.request().url());if(url.protocol==="blob:")return route.continue();const host=url.hostname;if(!["127.0.0.1","localhost"].includes(host))return route.abort();return route.continue();});});
async function start(page:import("@playwright/test").Page,eid:string){await page.goto(`/listening/${Number(eid.split("-")[1])}/${eid}`);await page.getByRole("button",{name:"Start Listening",exact:true}).or(page.getByRole("link",{name:"Resume practice",exact:true})).click();await page.waitForURL(/\/listening\/attempts\/[\w-]+$/);await expect(page.getByLabel("Listening audio player")).toBeVisible();await go(page,1);}
async function go(page:import("@playwright/test").Page,n:number){await page.getByRole('button',{name:/^Questions \d+\/40/}).click();await page.getByRole('button',{name:`Go to question ${n}`,exact:true}).click();}
async function showSource(page:import("@playwright/test").Page){const button=page.getByRole("button",{name:"Source material",exact:true});if(await button.isVisible())await button.click();}
async function showQuestions(page:import("@playwright/test").Page){const button=page.getByRole("button",{name:"Questions",exact:true});if(await button.isVisible())await button.click();}
async function time(page:import("@playwright/test").Page){return page.locator('audio').first().evaluate(el=>(el as HTMLAudioElement).currentTime);}
test("owned verified lifecycle, native audio, resume, transitions and review",async({page},info)=>{
 await page.goto('/listening');await expect(page.locator('main a[href*="cambridge-"]')).toHaveCount(72);
 await start(page,'cambridge-14-test-01');const url=page.url();await expect.poll(()=>page.locator("audio").first().evaluate(el=>(el as HTMLAudioElement).readyState)).toBeGreaterThan(0);await showSource(page);await expect.poll(()=>page.getByRole("button",{name:"Enlarge source image"}).first().locator("img").evaluate(el=>(el as HTMLImageElement).naturalWidth)).toBeGreaterThan(0);await page.screenshot({path:`.next/listening-workspace-${info.project.name}.png`});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);const player=page.getByRole('region',{name:'Listening audio player'});await expect(player.getByRole('button')).toHaveCount(3);await showQuestions(page);
 await page.getByRole('button',{name:'Play',exact:true}).click();await expect.poll(()=>time(page)).toBeGreaterThan(.2);
 await page.getByLabel('Question 1',{exact:true}).fill('Canadian');await page.getByLabel('Question 2',{exact:true}).fill('furniture');await expect(page.getByRole('button',{name:'Pause',exact:true})).toBeVisible();
 await page.getByLabel('Audio progress').fill('6');await page.getByRole('button',{name:'Pause',exact:true}).click();await page.getByRole('button',{name:'Back 5 seconds',exact:true}).click();expect(await time(page)).toBeLessThan(2);await page.getByRole('button',{name:'Forward 5 seconds',exact:true}).click();expect(await time(page)).toBeGreaterThan(5);
 await go(page,11);await expect(page.locator('#question-11')).toBeVisible();expect(await page.locator('audio').first().getAttribute('src')).toContain('/1');
 await page.locator('#question-11 input[type=radio]').first().check();await page.locator('#question-12 input[type=radio]').nth(2).check();
 await waitForSaved(page);await page.reload();await expect.poll(()=>time(page)).toBeGreaterThan(5);await expect(page.locator('#question-11 input[type=radio]').first()).toBeChecked();expect(await page.locator('audio').first().evaluate(el=>(el as HTMLAudioElement).paused)).toBe(true);
 await page.getByRole('button',{name:/^Part 2/}).click();await expect.poll(()=>page.locator('audio').first().getAttribute('src')).toContain('/2');expect(await page.locator('audio').first().evaluate(el=>(el as HTMLAudioElement).paused)).toBe(true);
 await page.getByRole('button',{name:'Play',exact:true}).click();await expect.poll(()=>time(page)).toBeGreaterThan(.1);await page.getByLabel('Audio progress').fill('11.9');await expect(page.getByText('Cambridge 14 · Listening · Part 3 of 4')).toBeAttached({timeout:10000});
 await page.getByRole('button',{name:/^Part 4/}).click();expect(await page.locator('audio').first().evaluate(el=>(el as HTMLAudioElement).paused)).toBe(true);await expect(page.getByText('Cambridge 14 · Listening · Part 4 of 4')).toBeAttached();
 await page.getByRole('button',{name:'Finish practice',exact:true}).click();await page.getByRole('button',{name:'Keep practising',exact:true}).click();await expect(page).toHaveURL(url);
 await page.getByRole('button',{name:'Finish practice',exact:true}).click();await page.getByRole('button',{name:'Finish and view results',exact:true}).click();await page.waitForURL(/\/results$/);await expect(page.getByText('Estimated practice band',{exact:true})).toBeVisible();await expect(page.getByText('4 / 40',{exact:true})).toBeVisible();
 await page.getByRole('link',{name:'Review all questions'}).click();await expect(page.getByRole('heading',{name:'Review your answers'})).toBeVisible();await expect(page.locator('#question-1')).toHaveAttribute('data-review-status','correct');await expect(page.locator('#question-1')).toContainText('Canadian');await expect(page.locator('input[aria-label="Question 1"]')).toHaveCount(0);
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await page.screenshot({path:`.next/listening-${info.project.name}.png`,fullPage:false});
});
test("preliminary, recovered Cambridge04 keys and source image viewer",async({page})=>{
 await start(page,'cambridge-21-test-02');for(const [n,value] of [[1,'13 January'],[2,'48'],[3,'pizza'],[4,'India']] as const)await page.getByLabel(`Question ${n}`,{exact:true}).fill(value);await waitForSaved(page);await page.getByRole('button',{name:'Finish practice',exact:true}).click();await page.getByRole('button',{name:'Finish and view results',exact:true}).click();await page.waitForURL(/\/results$/);await expect(page.getByText('Listening practice',{exact:true})).toBeVisible();await expect(page.getByText('Estimated practice band',{exact:true})).toBeVisible();
 await start(page,'cambridge-04-test-02');await page.locator('#question-1 input[type=radio]').first().check();await waitForSaved(page);await page.getByRole('button',{name:'Finish practice',exact:true}).click();await page.getByRole('button',{name:'Finish and view results',exact:true}).click();await page.waitForURL(/\/results$/);await expect(page.getByText('Listening practice',{exact:true})).toBeVisible();await expect(page.getByText('Estimated practice band',{exact:true})).toHaveCount(0);
 await start(page,'cambridge-14-test-02');await go(page,16);await page.getByRole('combobox',{name:'Question 16',exact:true}).selectOption('H');await showSource(page);const image=page.getByRole('button',{name:'Enlarge source image'}).first();await expect.poll(()=>image.locator("img").evaluate(el=>(el as HTMLImageElement).naturalWidth)).toBeGreaterThan(0);await image.click();await expect(page.getByRole('button',{name:'Close image'})).toBeVisible();await page.getByRole('button',{name:'Close image'}).click();expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
});
test("M4A, keyboard, retry and concurrent draft reconciliation",async({page})=>{
 await start(page,'cambridge-05-test-01');const id=page.url().split('/').pop()!;
 await expect.poll(()=>page.locator('audio').first().evaluate(el=>(el as HTMLAudioElement).readyState)).toBeGreaterThan(0);
 const head=await page.request.head(`/api/listening/audio/${id}/1`);expect(head.status()).toBe(200);expect(head.headers()['content-type']).toContain('audio/mp4');
 await page.getByRole('button',{name:'Play',exact:true}).click();await expect.poll(()=>time(page)).toBeGreaterThan(.1);await page.getByRole('button',{name:'Pause',exact:true}).click();
 await page.getByLabel('Audio progress').evaluate(el=>{const input=el as HTMLInputElement;Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value')!.set!.call(input,'6');input.dispatchEvent(new Event('input',{bubbles:true}));input.dispatchEvent(new Event('change',{bubbles:true}));});
 const input=page.getByLabel('Question 1',{exact:true});await input.focus();const before=await time(page);await page.keyboard.press('ArrowLeft');expect(Math.abs(await time(page)-before)).toBeLessThan(.2);
 await input.blur();await page.locator('main').click({position:{x:1,y:1}});await page.keyboard.press('Space');await expect.poll(()=>page.locator('audio').first().evaluate(el=>(el as HTMLAudioElement).paused)).toBe(false);await page.keyboard.press('Space');await expect.poll(()=>page.locator('audio').first().evaluate(el=>(el as HTMLAudioElement).paused)).toBe(true);
 await waitForSaved(page);
 const bodies:{event_id:string}[]=[];await page.route('**/api/alua/listening/attempts/*/sync',async route=>{bodies.push(route.request().postDataJSON());if(bodies.length===1)return route.abort();return route.continue();});
 await input.fill('first draft');await expect(page.getByRole('status').filter({hasText:/Offline or save interrupted/})).toBeVisible();await input.fill('newer local draft');await waitForSaved(page);expect(bodies.length).toBeGreaterThan(1);expect(bodies[0]!.event_id).toBe(bodies[1]!.event_id);await page.unroute('**/api/alua/listening/attempts/*/sync');
 const headers={Authorization:`Bearer ${process.env.ALUA_LISTENING_TEST_TOKEN}`};const endpoint=`/api/alua/listening/attempts/${id}`;const remote=await (await page.request.get(endpoint,{headers})).json();expect(remote.answers['cambridge-05-test-01-q01']).toBe('newer local draft');
 expect((await page.request.post(endpoint+'/sync',{headers,data:{event_id:crypto.randomUUID(),expected_version:remote.version,answers:{...remote.answers,'cambridge-05-test-01-q01':'remote edit'},state:remote.state}})).ok()).toBe(true);
 await input.fill('local conflict');await page.getByRole('button',{name:'Keep my local answers'}).click();await waitForSaved(page);await page.reload();await expect(page.getByLabel('Question 1',{exact:true})).toHaveValue('local conflict');
 const submits:{event_id:string}[]=[];await page.route('**/api/alua/listening/attempts/*/submit',async route=>{submits.push(route.request().postDataJSON());if(submits.length===1){await route.fetch();return route.abort();}return route.continue();});
 await page.getByRole('button',{name:'Finish practice',exact:true}).click();await page.getByRole('button',{name:'Finish and view results',exact:true}).click();await page.getByRole('button',{name:'Confirm pending finish',exact:true}).click();await page.getByRole('button',{name:'Finish and view results',exact:true}).click();await page.waitForURL(/\/results$/);expect(submits.length).toBe(2);expect(submits[0]!.event_id).toBe(submits[1]!.event_id);
});

test("split panes, independent scroll, source selection and adaptive groups",async({page},info)=>{
 await start(page,'cambridge-14-test-01');

 const source=page.getByRole('region',{name:'Listening source material',exact:true,includeHidden:true});
 const questions=page.getByRole('region',{name:'Listening questions',exact:true});
 const player=page.getByRole('region',{name:'Listening audio player'});
 await showSource(page);
 await expect.poll(()=>source.locator('img').first().evaluate(el=>(el as HTMLImageElement).naturalWidth)).toBeGreaterThan(0);
 const mobile=await page.getByRole('button',{name:'Source material',exact:true}).isVisible();
 if(!mobile){
  const left=(await source.boundingBox())!,right=(await questions.boundingBox())!;
  expect(left.width/(left.width+right.width)).toBeCloseTo(.55,2);
  const before=(await player.boundingBox())!;
  await source.evaluate(el=>{el.scrollTop=160;});
  expect(await source.evaluate(el=>el.scrollTop)).toBeGreaterThan(0);
  const offset=await source.evaluate(el=>el.scrollTop);
  await questions.evaluate(el=>{el.scrollTop=180;});
  expect(await questions.evaluate(el=>el.scrollTop)).toBeGreaterThan(0);
  expect(await source.evaluate(el=>el.scrollTop)).toBe(offset);
  expect((await player.boundingBox())!.y).toBe(before.y);
 }else{
  await expect(source).toBeVisible();await expect(questions).toBeHidden();
 }
 await source.getByRole('button',{name:'Enlarge source image'}).first().click();
 await expect(page.getByRole('button',{name:'Close image'})).toBeVisible();
 await page.keyboard.press('Escape');await expect(page.getByRole('button',{name:'Close image'})).toBeHidden();
 await showQuestions(page);await expect(questions).toBeVisible();
 await page.screenshot({path:`.next/listening-split-${info.project.name}.png`});
 // Navigation exposes the next group's shared options without changing the audio part.
 await go(page,11);
 await showSource(page);await expect(source.getByText('Answer bank',{exact:true})).toBeVisible();
 await expect(source.getByText('Questions 11–20',{exact:true})).toBeVisible();
 // Passive scroll can cross groups without replacing or resetting the other pane.
 await showQuestions(page);await questions.dispatchEvent('wheel',{deltaY:1000});
 await questions.evaluate(el=>{const next=el.querySelectorAll('[data-question-group]')[1]!;el.scrollTop+=next.getBoundingClientRect().top-el.getBoundingClientRect().top-20;});
 await expect(source.locator('header span')).toHaveText('Questions 11–20');
 await questions.evaluate(el=>{el.scrollTop=el.scrollHeight;});
 await expect(source.locator('header span')).toHaveText('Questions 11–20');
 await go(page,15);
 await expect(questions).toBeVisible();await showSource(page);
 await expect(source.getByText('Questions 11–20',{exact:true})).toBeVisible();
 expect(await page.locator('audio').first().getAttribute('src')).toContain('/1');
 // Structured groups can retain original pages on the part; keep them beside answers.
 await start(page,'cambridge-14-test-02');await showSource(page);await expect(source).toBeVisible();await showQuestions(page);
 await expect(questions).toBeVisible();
 expect(await questions.evaluate(el=>el.parentElement!.dataset.layout)).toBe("split");
 await go(page,16);
 await showSource(page);await expect(source).toBeVisible();
 await expect(source.getByText('Questions 11–20',{exact:true})).toBeVisible();
 await go(page,11);
 await expect(source).toHaveCount(1);await expect(questions).toBeVisible();
 await go(page,25);
 await showSource(page);await expect(source.getByText('Answer bank',{exact:true})).toBeVisible();await showQuestions(page);
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 expect(await page.evaluate(()=>document.documentElement.scrollHeight<=innerHeight+1)).toBe(true);
 await page.screenshot({path:`.next/listening-adaptive-${info.project.name}.png`});
});

test("V3 compact layout, resize, question grid and flags",async({page},info)=>{
 await start(page,'cambridge-14-test-01');
 const main=page.locator('main');const source=page.getByRole('region',{name:'Listening source material',includeHidden:true});const questions=page.getByRole('region',{name:'Listening questions'});
 const metrics=await main.evaluate(el=>Array.from(el.children).filter(c=>c.tagName!=='DIALOG').map(c=>({tag:c.tagName,height:c.getBoundingClientRect().height})));
 console.log('V3',info.project.name,JSON.stringify(metrics));
 expect(metrics[0]!.height).toBeGreaterThanOrEqual(110);expect(metrics[0]!.height).toBeLessThanOrEqual(140);
 expect((await page.locator('footer').boundingBox())!.height).toBeLessThanOrEqual(64);
 const bounds=(await questions.boundingBox())!;expect(bounds.height).toBeGreaterThan(page.viewportSize()!.height*.65);
 const divider=page.getByRole('separator',{name:'Resize Listening panels'});
 if(await divider.isVisible()){
  const box=(await divider.boundingBox())!;await page.mouse.move(box.x+box.width/2,box.y+120);await page.mouse.down();await page.mouse.move(page.viewportSize()!.width*.4,box.y+120);await page.mouse.up();await expect(divider).toHaveAttribute('aria-valuenow','40');
  await divider.focus();await page.keyboard.press('ArrowRight');await expect(divider).toHaveAttribute('aria-valuenow','42');await divider.dblclick();await expect(divider).toHaveAttribute('aria-valuenow','55');
 }
 await page.getByLabel('Question 1',{exact:true}).fill('Canadian');await page.getByRole('button',{name:'Mark question 1',exact:true}).click();
 await page.getByRole('button',{name:/^Questions \d+\/40/}).click();
 const grid=page.getByRole('navigation',{name:'Questions',exact:true});await expect(grid.getByRole('button')).toHaveCount(40);
 await expect(grid.getByRole('button',{name:'Go to question 1',exact:true})).toHaveAttribute('data-answered','true');await expect(grid.getByRole('button',{name:'Go to question 1',exact:true})).toHaveAttribute('data-marked','true');
 await page.screenshot({path:`docs/listening-workspace-v3/${info.project.name}-grid.png`});
 await grid.getByRole('button',{name:'Go to question 40',exact:true}).click();await expect(grid).toBeHidden();await expect(page.locator('#question-40')).toBeInViewport();await expect(page.locator('#question-40')).toHaveAttribute('data-current','true');
 expect(await page.locator('audio').first().getAttribute('src')).toContain('/1');expect(await page.locator('audio').first().evaluate(el=>(el as HTMLAudioElement).paused)).toBe(true);
 await page.getByRole('button',{name:'Previous question',exact:true}).click();await expect(page.locator('#question-39')).toBeInViewport();await page.getByRole('button',{name:'Next question',exact:true}).click();await expect(page.locator('#question-40')).toBeInViewport();
 await go(page,1);await showSource(page);await expect.poll(()=>source.locator('img').first().evaluate(el=>(el as HTMLImageElement).naturalWidth)).toBeGreaterThan(0);
 await page.screenshot({path:`docs/listening-workspace-v3/${info.project.name}.png`});await showQuestions(page);await page.screenshot({path:`docs/listening-workspace-v3/${info.project.name}-questions.png`});
 await page.reload();await expect(page.getByLabel('Question 1',{exact:true})).toHaveValue('Canadian');await expect(page.getByRole('button',{name:'Unmark question 1',exact:true})).toHaveAttribute('aria-pressed','true');
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth&&document.documentElement.scrollHeight<=innerHeight+1)).toBe(true);
 const footer=(await page.locator('footer').boundingBox())!,panel=(await questions.boundingBox())!;expect(panel.y+panel.height).toBeLessThanOrEqual(footer.y+1);
});

test("manual track switch cancels pending automatic playback",async({page})=>{
 await start(page,'cambridge-14-test-02');
 await page.getByRole('button',{name:/^Part 1/}).click();await expect(page.locator('audio').first()).toHaveAttribute('src',/\/1$/);
 let release!:()=>void;const pending=new Promise<void>(resolve=>{release=resolve;});
 await page.route('**/api/listening/audio/*/3',async route=>{await pending;await route.continue();});
 try{
  await page.getByRole('button',{name:/^Part 2/}).click();
  await expect.poll(()=>page.locator('audio').first().evaluate(el=>(el as HTMLAudioElement).readyState)).toBeGreaterThan(0);
  await page.getByRole('button',{name:'Play',exact:true}).click();await expect.poll(()=>time(page)).toBeGreaterThan(.1);
  await page.getByLabel('Audio progress').fill('11.9');
  await expect(page.getByText('Cambridge 14 · Listening · Part 3 of 4')).toBeAttached();
  await page.getByRole('button',{name:/^Part 4/}).click();
  await expect(page.locator('audio').first()).toHaveAttribute('src',/\/4$/);
  await expect.poll(()=>page.locator('audio').first().evaluate(el=>(el as HTMLAudioElement).readyState)).toBeGreaterThan(0);
  expect(await page.locator('audio').first().getAttribute('src')).toContain('/4');
  expect(await page.locator('audio').first().evaluate(el=>(el as HTMLAudioElement).paused)).toBe(true);
 }finally{release();}
});

// Use real dataset bytes, including the recovered C04 T1 source.
// Only this snapshot transport is mocked; normal lifecycle checks use the real API.
function realExam(eid:string):Exam{return JSON.parse(readFileSync(resolve("../backend/app/content/listening_v1/exams",`${eid}.json`),"utf8"));}
async function recoveredSourceSnapshot(page:import("@playwright/test").Page){
 const exam=realExam('cambridge-04-test-01');const id='00000000-0000-4000-8000-000000000401';
 const snapshot:Attempt={id,exam_id:exam.exam_id,status:'in_progress',version:1,mode:'preliminary',content_hash:'read-only-real-source-check',answers:{},state:{displayed_part:1,current_question:1,audio_part:1,playback_seconds:0,marked:[]},exam};
 await page.route(`**/api/alua/listening/attempts/${id}**`,async route=>{
  const assetId=route.request().url().split('/assets/')[1];
  if(assetId){const asset=exam.assets.find(a=>a.asset_id===assetId)!;return route.fulfill({status:200,contentType:asset.relative_path.endsWith('.png')?'image/png':'image/jpeg',body:readFileSync(resolve('../backend/app/content/listening_v1',asset.relative_path))});}
  if(route.request().url().endsWith('/sync')){const body=route.request().postDataJSON();snapshot.state=body.state;snapshot.answers=body.answers;snapshot.version++;}
  return route.fulfill({status:200,json:snapshot});
 });
 await page.route('**/api/listening/authorize',route=>route.request().postDataJSON().attempt_id===id?route.fulfill({status:200,json:{}}):route.fallback());
 await page.goto(`/listening/attempts/${id}`);await expect(page.getByLabel('Listening audio player')).toBeVisible();await go(page,1);
}
test("real dataset source visibility and original page identity",async({page},info)=>{
 const baseline=process.env.ALUA_LISTENING_SOURCE_BASELINE==='1';const folder=`docs/listening-source-fix/${baseline?'before':'after'}`;
 const source=page.getByRole('region',{name:'Listening source material',exact:true,includeHidden:true});
 const questions=page.getByRole('region',{name:'Listening questions',exact:true});
 async function capture(name:string,expectedIds:string[],range:string){
  const [lo,hi]=range.match(/\d+/g)!.map(Number);
  const materials=Object.values(visualPolicy.parts).flatMap(p=>p.materials);
  expectedIds=expectedIds.filter(id=>materials.some(m=>m.asset_id===id&&m.question_range[0]!<=hi!&&lo!<=m.question_range[1]!));
  await expect(page.getByLabel("Listening audio player")).toBeVisible();
  await showSource(page);
  if(baseline&&await source.isVisible()&&await source.locator('img').count())await expect.poll(()=>source.locator('img').first().evaluate(el=>(el as HTMLImageElement).naturalWidth)).toBeGreaterThan(0);
  if(!baseline){
   await expect(source).toBeVisible();await expect(source.locator('header span')).toHaveText(range);
   for(const aid of expectedIds){const image=source.locator(`[data-source-asset="${aid}"] img`).first();await expect(image).toBeVisible();await expect.poll(()=>image.evaluate(el=>(el as HTMLImageElement).naturalWidth)).toBeGreaterThan(0);const digest=await image.evaluate(async el=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',await(await fetch((el as HTMLImageElement).src)).arrayBuffer()))).map(n=>n.toString(16).padStart(2,'0')).join(''));expect(digest).toBe(aid.slice('asset-'.length));}
   if(!await page.getByRole('button',{name:'Source material',exact:true}).isVisible()){
    const left=(await source.boundingBox())!,right=(await questions.boundingBox())!;expect(left.x+left.width).toBeLessThanOrEqual(right.x+1);await expect(questions).toBeVisible();
   }
  }
  await page.screenshot({path:`${folder}/${info.project.name}-${name}.png`});await showQuestions(page);
 }
 await recoveredSourceSnapshot(page);
 await capture('c04-t1-q1',realExam('cambridge-04-test-01').parts[0]!.supporting_assets,'Questions 1–10');
 if(!baseline){await go(page,5);await capture('c04-t1-q5',realExam('cambridge-04-test-01').parts[0]!.supporting_assets,'Questions 1–10');await go(page,1);await page.reload();await capture('c04-t1-reload',realExam('cambridge-04-test-01').parts[0]!.supporting_assets,'Questions 1–10');}
 await start(page,'cambridge-04-test-03');
 await capture('accommodation-q1',realExam('cambridge-04-test-03').parts[0]!.supporting_assets,'Questions 1–10');
 const accommodation=await source.locator('img').first().getAttribute('src');
 await go(page,2);await capture('accommodation-q2',realExam('cambridge-04-test-03').parts[0]!.supporting_assets,'Questions 1–10');
 if(!baseline)expect(await source.locator('img').first().getAttribute('src')).toBe(accommodation);
 await go(page,5);await capture('c04-t3-q5',realExam('cambridge-04-test-03').parts[0]!.supporting_assets,'Questions 1–10');
 await go(page,1);await page.reload();await capture('accommodation-reload',realExam('cambridge-04-test-03').parts[0]!.supporting_assets,'Questions 1–10');
 await start(page,'cambridge-14-test-02');
 await capture('c14-t2-q1',realExam('cambridge-14-test-02').parts[0]!.supporting_assets,'Questions 1–10');
 await go(page,25);await capture('c14-t2-shared-options',realExam('cambridge-14-test-02').parts[2]!.supporting_assets,'Questions 21–30');
 if(!baseline){await showSource(page);await expect(source.getByText('Answer bank',{exact:true})).toBeVisible();await showQuestions(page);}
 await start(page,'cambridge-14-test-01');
 for(const [n,range] of [[1,'Questions 1–10'],[11,'Questions 11–20'],[12,'Questions 11–20'],[13,'Questions 11–20'],[15,'Questions 11–20'],[21,'Questions 21–30'],[1,'Questions 1–10']] as const){await go(page,n);await capture(`c14-t1-q${n}`,realExam('cambridge-14-test-01').parts[Math.ceil(n/10)-1]!.supporting_assets,range);}
 if(!baseline){
  const divider=page.getByRole('separator',{name:'Resize Listening panels'});if(await divider.isVisible()){const box=(await divider.boundingBox())!;await page.mouse.move(box.x+7,box.y+80);await page.mouse.down();await page.mouse.move(page.viewportSize()!.width*.45,box.y+80);await page.mouse.up();await expect(divider).toHaveAttribute('aria-valuenow','45');await divider.dblclick();await expect(divider).toHaveAttribute('aria-valuenow','55');}
  await page.reload();await capture('c14-t1-reload',realExam('cambridge-14-test-01').parts[0]!.supporting_assets,'Questions 1–10');
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth&&document.documentElement.scrollHeight<=innerHeight+1)).toBe(true);
 }
});

test("source resolver preserves real page references and reports missing originals",()=>{
 const exam=realExam('cambridge-14-test-01'),part=exam.parts[0]!,group=part.groups[0]!;
 const original=[...group.supporting_assets];
 group.supporting_assets=[];
 expect(sourceMaterial(exam,part,group).assets).toEqual(original); // authoritative content blocks
 group.content_blocks=group.content_blocks.filter(block=>block.kind!=='original_source_image');
 for(const q of group.questions)delete q.visual_binding;
 expect(sourceMaterial(exam,part,group).assets).toEqual(part.supporting_assets); // part-owned originals
 expect(displayedPart(exam,11,1).part_number).toBe(2); // restored state disagreement
 part.supporting_assets=[];
 expect(sourceMaterial(exam,part,group).assets).toEqual(original); // reviewed metadata survives legacy empty bindings
 const available=exam.assets;exam.assets=[];
 expect(sourceMaterial(exam,part,group)).toMatchObject({hasMaterial:true,missing:original});
 exam.assets=available;delete part.visual_materials;exam.exam_id='unknown-legacy';
 group.supporting_assets=['missing-original'];
 expect(sourceMaterial(exam,part,group).missing).toEqual(['missing-original']);
 const structured=realExam('cambridge-14-test-02'),shared=structured.parts[2]!,bank=shared.groups[1]!;
 structured.exam_id='unknown-legacy';delete shared.visual_materials;
 shared.supporting_assets=[];bank.supporting_assets=[];bank.content_blocks=[];
 expect(sourceMaterial(structured,shared,bank).hasMaterial).toBe(true); // shared options are material
 bank.answer_bank=null;bank.questions.forEach(q=>{delete q.visual_binding;});
 expect(sourceMaterial(structured,shared,bank).hasMaterial).toBe(false); // genuinely self-contained
});

test("source fallback and image retry preserve the real workspace",async({page})=>{
 await start(page,'cambridge-14-test-01');
 const source=page.getByRole('region',{name:'Listening source material',includeHidden:true});
 const asset=realExam('cambridge-14-test-01').parts[0]!.supporting_assets[0]!;
 const pattern=`**/api/alua/listening/attempts/*/assets/${asset}`;
 await page.route(pattern,route=>route.fulfill({status:404,json:{detail:'Unavailable original'}}));
 await page.reload();await expect(page.getByLabel("Listening audio player")).toBeVisible();await showSource(page);
 const original=source.locator(`[data-source-asset="${asset}"]`);
 await expect(original.getByRole('alert')).toContainText('Original Cambridge source image could not load');
 await page.unroute(pattern);await original.getByRole('button',{name:'Retry image',exact:true}).click();
 await expect.poll(()=>original.locator('img').first().evaluate(el=>(el as HTMLImageElement).naturalWidth)).toBeGreaterThan(0);
 await showQuestions(page);await go(page,1);await waitForSaved(page);
 const endpoint=`**/api/alua/listening/attempts/${page.url().split('/').pop()}`;
 await page.route(endpoint,async route=>{
  const response=await route.fetch();const data=await response.json();const group=data.exam.parts[0].groups[0];
  group.supporting_assets=[];group.content_blocks=group.content_blocks.filter((b:{kind:string})=>b.kind!=='original_source_image');
  group.questions.forEach((q:{visual_binding?:unknown})=>{delete q.visual_binding;});data.exam.parts[0].supporting_assets=[];
  data.exam.assets=[]; // actual missing allowlist, rather than recoverable empty legacy bindings
  await route.fulfill({response,json:data});
 });
 await page.reload();await expect(page.getByLabel("Listening audio player")).toBeVisible();await showSource(page);await expect(source).toBeVisible();await expect(source.getByRole('alert')).toContainText('original source image is missing');
});

async function waitForSaved(page:import("@playwright/test").Page){
 await expect.poll(()=>page.evaluate(()=>Object.keys(localStorage).filter(key=>key.startsWith("alua:listening:")&&key.includes(`:${location.pathname.split("/").pop()}:`)).every(key=>{const d=JSON.parse(localStorage.getItem(key)!);return !d.pending&&d.serial<=d.savedSerial})),{timeout:20000}).toBe(true);
}
test("exam UI: centered Finish, silent autosave, reload and visible save errors",async({page},info)=>{
 await start(page,"cambridge-14-test-01");await showQuestions(page);await watchSaveIndicators(page);
 const input=page.getByLabel("Question 1",{exact:true});await input.fill("Canadian");await waitForSaved(page);await expectNoSaveIndicators(page);
 const endpoint=`/api/alua/listening/attempts/${page.url().split('/').pop()!}`;
 const headers={Authorization:`Bearer ${process.env.ALUA_LISTENING_TEST_TOKEN}`};
 await expect.poll(async()=>{const r=await page.request.get(endpoint,{headers});return (await r.json()).answers["cambridge-14-test-01-q01"]}).toBe("Canadian");
 await page.reload();await expect(page.getByLabel("Listening audio player")).toBeVisible();await showQuestions(page);await expect(input).toHaveValue("Canadian");await watchSaveIndicators(page);
 let fail=true;await page.route("**/api/alua/listening/attempts/*/sync",route=>fail?route.abort():route.continue());
 await input.fill("retry draft");await expect(page.getByRole("status").filter({hasText:/Offline or save interrupted/})).toBeVisible();await expectNoSaveIndicators(page);
 fail=false;await waitForSaved(page);await expectNoSaveIndicators(page);await page.unroute("**/api/alua/listening/attempts/*/sync");
 await page.getByRole("region",{name:"Listening questions",exact:true}).evaluate(el=>{el.scrollTop=300});await page.locator("main").evaluate(el=>{el.style.transform="translateZ(0)"});
 await page.getByRole("button",{name:"Finish practice",exact:true}).click();const dialog=page.getByRole("dialog",{name:"Finish this practice?",exact:true});await expectCenteredDialog(page,dialog);
 await page.screenshot({path:`.next/exam-ui-${info.project.name}.png`});
 await page.getByRole("button",{name:"Keep practising",exact:true}).click();await expect(dialog).toBeHidden();
 await page.getByRole("button",{name:"Finish practice",exact:true}).click();await page.keyboard.press("Escape");await expect(dialog).toBeHidden();
 if(page.viewportSize()!.width<760){await page.setViewportSize({width:390,height:320});await page.getByRole("button",{name:"Finish practice",exact:true}).click();await expectCenteredDialog(page,dialog);await expect(dialog.getByRole("button",{name:"Finish and view results",exact:true})).toBeInViewport();await page.keyboard.press("Escape");}
});


test("catalog preserves metadata while hiding every content status",async({page})=>{
 await page.goto('/listening');
 const response=await page.request.get('/api/alua/listening/exams',{headers:{Authorization:`Bearer ${process.env.ALUA_LISTENING_TEST_TOKEN}`}});
 expect(response.ok()).toBe(true);
 const {items}=await response.json();expect(items).toHaveLength(72);
 for(const entry of items){
  const card=page.locator(`main a[href="/listening/${entry.book}/${entry.exam_id}"]`);
  await expect(card).toHaveCount(1);
  await expect(card.locator('[data-mode]')).toHaveCount(0);
  await expect(card).not.toContainText(/Verified|Preliminary|Ungraded|Unavailable/);
 }
});

test("recovered original question 34 and repaired pages stay usable in V3",async({page})=>{
 for(const [eid,n] of [['cambridge-04-test-01',34],['cambridge-06-test-02',6],['cambridge-14-test-03',1]] as const){
  await start(page,eid);await go(page,n);await showSource(page);
  const source=page.getByRole('region',{name:'Listening source material',includeHidden:true});
  await expect.poll(()=>source.locator('img').last().evaluate(el=>(el as HTMLImageElement).naturalWidth)).toBeGreaterThan(0);
  await showQuestions(page);await expect(page.getByLabel(`Question ${n}`,{exact:true})).toBeVisible();
  await page.getByLabel(`Question ${n}`,{exact:true}).fill('restored answer');
  const endpoint=`/api/alua/listening/attempts/${page.url().split('/').pop()!}`;
  await expect.poll(async()=>{const response=await page.request.get(endpoint,{headers:{Authorization:`Bearer ${process.env.ALUA_LISTENING_TEST_TOKEN}`}});return (await response.json()).answers[`${eid}-q${String(n).padStart(2,'0')}`];}).toBe('restored answer');
 }
});

test("Soft Capsules player and independently scrolling panels",async({page},info)=>{
 await start(page,'cambridge-14-test-01');await page.getByLabel('Question 1',{exact:true}).fill('');await waitForSaved(page);
 const player=page.getByRole('region',{name:'Listening audio player'});
 const source=page.getByRole('region',{name:'Listening source material',includeHidden:true});
 const questions=page.getByRole('region',{name:'Listening questions',exact:true});
 await expect.poll(()=>page.locator('audio').first().evaluate(el=>(el as HTMLAudioElement).readyState)).toBeGreaterThan(0);
 await page.getByRole('button',{name:'Play',exact:true}).click();await expect.poll(()=>time(page)).toBeGreaterThan(.1);
 await page.getByLabel('Audio progress').fill('6');
 // Let the short progress transition settle before recording the visual.
 await expect.poll(()=>time(page)).toBeGreaterThan(6.2);
 await page.getByLabel('Audio progress').evaluate(el=>(el as HTMLElement).blur());
 await page.screenshot({path:`docs/listening-workspace-v3/soft-capsules/after-${info.project.name}.png`});
 {
  await expect(player.locator('[data-waveform=soft-capsules]')).toHaveAttribute('data-playing','true');
  await expect(player.locator('[data-waveform-progress]')).toHaveAttribute('width',/^[1-9]/);
 }
 await page.getByRole('button',{name:'Pause',exact:true}).click();
 await expect(player.locator('[data-waveform=soft-capsules]')).toHaveAttribute('data-playing','false');
 await page.emulateMedia({reducedMotion:'reduce'});
 expect(await player.locator('svg g:last-child line').first().evaluate(el=>getComputedStyle(el).animationName)).toBe('none');
 await page.emulateMedia({reducedMotion:'no-preference'});
 const range=page.getByLabel('Audio progress'),pausedTime=await time(page);
 await range.focus();await page.keyboard.press('ArrowRight');await expect.poll(()=>time(page)).toBeGreaterThan(pausedTime);
 const track=(await range.boundingBox())!;await range.click({position:{x:track.width*.25,y:track.height/2}});await expect.poll(()=>time(page)).toBeLessThan(5);
 await go(page,11);await showSource(page);
 await expect.poll(()=>source.locator('img').first().evaluate(el=>(el as HTMLImageElement).naturalWidth)).toBeGreaterThan(0);
 const mobile=await page.getByRole('button',{name:'Source material',exact:true}).isVisible();
 const assets=await source.locator('[data-source-asset]').evaluateAll(els=>els.map(el=>el.getAttribute('data-source-asset')));
 const sourceBefore=await source.evaluate(el=>{el.scrollTop=180;return el.scrollTop;});
 await showQuestions(page);await questions.dispatchEvent('wheel',{deltaY:1000});
 await questions.evaluate(el=>{const group=el.querySelectorAll('[data-question-group]')[1]!;el.scrollTop+=group.getBoundingClientRect().top-el.getBoundingClientRect().top-20;});

 await expect(source.locator('header span')).toHaveText('Questions 11–20');
 expect(await source.locator('[data-source-asset]').evaluateAll(els=>els.map(el=>el.getAttribute('data-source-asset')))).toEqual(assets);
 const right=await questions.evaluate(el=>el.scrollTop);
 await showSource(page);expect(await source.evaluate(el=>el.scrollTop)).toBe(sourceBefore);
 await source.evaluate(el=>{el.scrollTop+=80;});
 await showQuestions(page);expect(await questions.evaluate(el=>el.scrollTop)).toBe(right);
 // Explicit navigation scrolls the target while retaining all Part sources.
 await go(page,15);await expect(page.locator('#question-15')).toBeInViewport();await showSource(page);await expect(source.locator('header span')).toHaveText('Questions 11–20');
 await showQuestions(page);await go(page,1);await page.getByLabel('Question 1',{exact:true}).fill('Canadian');await waitForSaved(page);
 const leftOffset=await source.evaluate(el=>el.scrollTop),rightOffset=await questions.evaluate(el=>el.scrollTop);
 await page.getByLabel('Audio progress').fill('7');await waitForSaved(page);
 await expect.poll(()=>questions.evaluate(el=>el.scrollTop)).toBe(rightOffset);
 expect(await source.evaluate(el=>el.scrollTop)).toBe(leftOffset);
 await page.reload();await expect(page.getByLabel('Question 1',{exact:true})).toHaveValue('Canadian');
 await expect.poll(()=>time(page)).toBeGreaterThan(6);
 expect(await page.evaluate(()=>document.documentElement.scrollHeight<=innerHeight+1&&document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 if(!mobile)await expect(page.getByRole('separator',{name:'Resize Listening panels'})).toBeVisible();
});
