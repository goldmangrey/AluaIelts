import {test,expect,type Page} from '@playwright/test';
import {mkdirSync} from 'node:fs';
import {resolve} from 'node:path';
import {fixture,loadReview,attemptId} from './review-focus-fixture';

test.use({video:'on'});
const output=resolve('../work/ai-typewriter');mkdirSync(output,{recursive:true});
const unicode='Кириллица и English, café, á, 👩‍👩‍👧‍👦 и 🐉. ';
const prose=unicode.repeat(7);
async function setup(page:Page,skill:'reading'|'listening',saved=false,unanswered=false){
 if(skill==='listening')for(const n of [2,3]){const row=fixture.listening.questions.find((q:{question_number:number})=>q.question_number===n);row.correct=false;row.user_answer=unanswered?'':'fixture wrong';}
 if(skill==='reading'){const row=fixture.reading.positions[1];row.user_answer=unanswered?'':'wrong';row.unanswered=unanswered;row.is_correct=false;}
 await loadReview(page,skill);let calls=0;
 const responses=new Map<string,object>();
 const response=(id:string)=>{
  if(skill==='listening')return {cached:saved,what_happened:`Question ${id}. ${prose}`,why:prose,next_time:'Check the final detail.',evidence:{available:true,reason:null,part:1,quote:'Transcript fixture quote',segment_ids:['seg-0001'],clip_start:1,clip_end:2}};
  const passage=fixture.readingExam.passages.find((p:{question_groups:{questions:{id:string}[]}[]})=>p.question_groups.some(g=>g.questions.some(q=>q.id===id)));
  const block=passage.content.findIndex((b:{text:string})=>b.text.length>100),text=passage.content[block].text;
  return {question_id:id,fingerprint:'typewriter-'+id,cached:saved,source_status:'needs_review',review:{why_user_answer_wrong:`Question ${id}. ${prose}`,why_correct_answer_works:prose,ielts_tip:'Read the complete question.',evidence_status:'found',reason:null,evidence:[{passage_id:passage.id,block_index:block,start:0,end:80,quote:text.slice(0,80),kind:'support'}]}};
 };
 await page.route(`**/api/alua/practice/reviews/${skill}/${attemptId}*`,async route=>{
  const id=new URL(route.request().url()).searchParams.get('question');await new Promise(r=>setTimeout(r,40));
  return route.fulfill({json:id?{response:responses.get(id)??(saved?response(id):null)}:{questions:[...responses.keys()]}});
 });
 await page.route(`**/api/${skill}/review`,async route=>{calls++;const body=route.request().postDataJSON(),id=String(body.question_id??body.question_number),data=response(id);await new Promise(r=>setTimeout(r,120));responses.set(id,data);return route.fulfill({json:data});});
 const mobile=page.viewportSize()!.width<720;
 if(mobile)await page.getByRole('button',{name:'Questions',exact:true}).click();
 const card=(n:number)=>page.getByRole('region',{name:`AI explanation for question ${n}`,exact:true});
 const open=async(n:number)=>{
  if(skill==='reading')await page.getByRole('button',{name:new RegExp(`^(Explain question ${n} with AI|View AI explanation for question ${n})$`)}).click();
  else await page.locator(`#question-${n}`).getByRole('button',{name:/Explain with AI|View AI Explanation/}).click();
 };
 const close=async(n:number)=>{
  if(skill==='reading')await card(n).getByRole('button',{name:'Close AI explanation'}).click();else await open(n);
 };
 return {calls:()=>calls,card,open,close,mobile};
}
for(const skill of ['reading','listening'] as const){
 test(`${skill}: unanswered uses existing review, evidence controls and saved cache`,async({page},info)=>{
  await page.emulateMedia({reducedMotion:'reduce'});
  const ui=await setup(page,skill,false,true);
  const answer=page.locator(skill==='reading'?'[data-question="2"]':'#question-2');
  await expect(answer).toContainText('Not answered');
  await expect(answer).toContainText('Correct answer');
  await ui.open(2);const card=ui.card(2);
  await expect(card.locator('[data-ai-typing]')).toHaveAttribute('data-ai-typing','false');
  if(skill==='reading'){
   await expect(card).toContainText('Finding the answer');
   await card.getByRole('button',{name:'Show in passage'}).click();
   await expect(page.locator('[data-reading-ai="true"]').first()).toBeVisible();
   await page.getByRole('button',{name:/Back to Q2$/}).click();
  }else{
   await card.getByRole('button',{name:'Play Moment'}).click();
   await expect(page.getByRole('button',{name:'Pause',exact:true})).toBeVisible();
   await card.getByRole('button',{name:'Loop Moment'}).click();
   await expect(card.getByRole('button',{name:'Loop Moment'})).toHaveAttribute('aria-pressed','true');
  }
  await page.screenshot({path:resolve(output,`${skill}-${info.project.name}-unanswered.png`)});
  await ui.close(2);await ui.open(2);expect(ui.calls()).toBe(1);
  await page.reload();if(ui.mobile)await page.getByRole('button',{name:'Questions',exact:true}).click();
  const trigger=skill==='reading'?page.getByRole('button',{name:'View AI explanation for question 2',exact:true}):page.locator('#question-2').getByRole('button',{name:'View AI Explanation',exact:true});
  await expect(trigger).toBeVisible();if(await trigger.getAttribute('aria-expanded')!=='true')await trigger.click();
  await expect(ui.card(2)).toBeVisible();expect(ui.calls()).toBe(1);
  await expect(page.locator(skill==='reading'?'[data-question="2"]':'#question-2')).toContainText('Not answered');
 });

 test(`${skill}: progressive Unicode, cursor, Skip, stable layout, replay and evidence actions`,async({page,context},info)=>{
  const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));const ui=await setup(page,skill);
  await ui.open(2);const card=ui.card(2),typing=card.locator('[data-ai-typing]');
  await expect(typing).toHaveAttribute('data-ai-typing','true');
  const text=typing.locator('[aria-live="off"]'),first=await text.innerText();
  await expect.poll(async()=>(await text.innerText()).length).toBeGreaterThan(first.length+55);
  await expect(card.locator('[data-ai-cursor]')).toHaveCount(1);
  if(ui.mobile&&skill==='reading')await text.locator('p').first().scrollIntoViewIfNeeded();
  const bounds=await card.boundingBox(),panel=page.locator(skill==='reading'?'[aria-label="Reading questions"]':'[aria-label="Listening questions"]');
  const scroll=await panel.evaluate(el=>el.scrollTop);
  const cursorWidth=await card.locator('[data-ai-cursor]').evaluate(el=>{const range=document.createRange();range.selectNodeContents(el);return range.getBoundingClientRect().width;});expect(cursorWidth).toBeGreaterThan(0);
  await page.screenshot({path:resolve(output,`${skill}-${info.project.name}-typing.png`)});
  await card.getByRole('button',{name:'Skip animation'}).evaluate(el=>(el as HTMLButtonElement).click());
  await expect(typing).toHaveAttribute('data-ai-typing','false');await expect(text).toContainText(unicode.trim());
  await expect(card.locator('[data-ai-cursor]')).toHaveCount(0);
  expect(Math.abs((await card.boundingBox())!.height-bounds!.height)).toBeLessThan(2);expect(await panel.evaluate(el=>el.scrollTop)).toBe(scroll);
  await expect(card.getByText('Saved explanation')).toHaveCount(0);await expect(card.getByText('Используется сохранённый текст.',{exact:false})).toHaveCount(0);
  if(skill==='reading'){
   await expect(card).toContainText('В исходном тексте возможны неточности.');
   await card.getByRole('button',{name:'Show in passage'}).click();await expect(page.locator('[data-reading-ai="true"]').first()).toBeVisible();
   await page.getByRole('button',{name:/Back to Q2$/}).click();
  }else{
   await card.getByRole('button',{name:'Play Moment'}).click();await expect(page.getByRole('button',{name:'Pause',exact:true})).toBeVisible();
   await card.getByRole('button',{name:'Loop Moment'}).click();await expect(card.getByRole('button',{name:'Loop Moment'})).toHaveAttribute('aria-pressed','true');
   await card.getByText('Transcript quote',{exact:true}).click();await expect(card.getByRole('blockquote')).toContainText('Transcript fixture quote');
  }
  await ui.close(2);await ui.open(2);await expect(card.locator('[data-ai-typing]')).toHaveAttribute('data-ai-typing','false');expect(ui.calls()).toBe(1);
  await page.reload();if(ui.mobile)await page.getByRole('button',{name:'Questions',exact:true}).click();
  const savedTrigger=skill==='reading'?page.getByRole('button',{name:'View AI explanation for question 2',exact:true}):page.locator('#question-2').getByRole('button',{name:'View AI Explanation',exact:true});
  await expect(savedTrigger).toBeVisible();if(await savedTrigger.getAttribute('aria-expanded')!=='true')await savedTrigger.click();
  await expect(card).toBeVisible();await expect(card.locator('[data-ai-typing]')).toHaveAttribute('data-ai-typing','false');expect(ui.calls()).toBe(1);
  expect(errors).toEqual([]);
  const video=page.video();await context.close();if(video)await video.saveAs(resolve(output,`${skill}-${info.project.name}.webm`));
 });
 test(`${skill}: natural completion removes the cursor`,async({page})=>{
  await page.clock.install();const ui=await setup(page,skill);await ui.open(2);
  await expect(ui.card(2).locator('[data-ai-cursor]')).toHaveCount(1);
  await page.clock.fastForward(16000);
  await expect(ui.card(2).locator('[data-ai-typing]')).toHaveAttribute('data-ai-typing','false');
  await expect(ui.card(2).locator('[data-ai-cursor]')).toHaveCount(0);
  await expect(ui.card(2).locator('[aria-live="off"]')).toContainText(unicode.trim());
 });
 test(`${skill}: saved response has zero AI POSTs; reduced motion is immediate`,async({page})=>{
  await page.emulateMedia({reducedMotion:'reduce'});const ui=await setup(page,skill,true);await ui.open(2);
  await expect(ui.card(2).locator('[data-ai-typing]')).toHaveAttribute('data-ai-typing','false');
  await expect(ui.card(2).locator('[aria-live="off"]')).toContainText(unicode.trim());
  await expect(ui.card(2).getByRole('button',{name:'Skip animation'})).toHaveCount(0);expect(ui.calls()).toBe(0);
 });
 test(`${skill}: switching questions cancels the old cursor without mixing prose`,async({page})=>{
  const ui=await setup(page,skill);await ui.open(2);await expect(ui.card(2).locator('[data-ai-cursor]')).toHaveCount(1);
  await ui.open(skill==='reading'?1:3);const next=skill==='reading'?1:3;
  await expect(ui.card(2).locator('[data-ai-cursor]')).toHaveCount(0);await expect(ui.card(next).locator('[data-ai-cursor]')).toHaveCount(1);
  await ui.card(next).getByRole('button',{name:'Skip animation'}).click();
  await expect(ui.card(next).locator('[aria-live="off"]')).toContainText(skill==='reading'?fixture.reading.positions[0].question_id:'Question 3.');
  expect(ui.calls()).toBe(2);
 });
}
