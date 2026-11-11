import {test,expect} from '@playwright/test';
import {mkdirSync} from 'node:fs';
import {fixture,loadReview} from './review-focus-fixture';
const screenshots='docs/ai-ux-hotfix';
test('unavailable Reading evidence never claims an exact citation',async({page},info)=>{
 await loadReview(page,'reading');
 await page.route('**/api/reading/review',async route=>route.fulfill({json:{
  question_id:route.request().postDataJSON().question_id,fingerprint:'fixture',cached:false,source_status:'needs_review',
  review:{why_user_answer_wrong:'Нет подтверждённого контекста.',why_correct_answer_works:'Подтверждение недоступно.',ielts_tip:'Сравните условие с текстом.',evidence_status:'unavailable',evidence:[],reason:'evidence_not_found'}
 }}));
 if(info.project.name.includes('mobile'))await page.getByRole('button',{name:'Questions',exact:true}).click();
 await page.getByRole('button',{name:'Explain question 1 with AI',exact:true}).click();
 const card=page.getByRole('region',{name:'AI explanation for question 1',exact:true});
 await expect(card).toContainText('Подсветка недоступна');
 await expect(card.getByText('Цитата точно относится',{exact:false})).toHaveCount(0);
 await expect(card.getByRole('button',{name:'Show in passage'})).toHaveCount(0);
 await expect(card.getByRole('button',{name:'Retry',exact:true})).toHaveCount(0);
});
test('temporary unavailable retries a fresh request and retains only found in memory',async({page},info)=>{
 await loadReview(page,'reading');let calls=0;
 const passage=fixture.readingExam.passages[0],block=passage.content.findIndex((b:{type:string;text:string})=>b.type==='paragraph'&&b.text.length>100);
 await page.route('**/api/reading/review',async route=>{
  calls++;const found=calls>=3;await new Promise(r=>setTimeout(r,80));
  await route.fulfill({json:{question_id:route.request().postDataJSON().question_id,fingerprint:'fixture',cached:false,source_status:'needs_review',retryable:!found,
   review:{why_user_answer_wrong:'Сравните ответ с текстом.',why_correct_answer_works:'Сохранённый контекст подтверждает объяснение.',ielts_tip:'Проверьте условие.',evidence_status:found?'found':'unavailable',reason:found?null:'models_unavailable',evidence:found?[{passage_id:passage.id,block_index:block,start:0,end:80,quote:passage.content[block].text.slice(0,80),kind:'support'}]:[]}}});
 });
 if(info.project.name.includes('mobile'))await page.getByRole('button',{name:'Questions',exact:true}).click();
 const trigger=page.getByRole('button',{name:'Explain question 1 with AI',exact:true}),card=page.getByRole('region',{name:'AI explanation for question 1',exact:true});
 await trigger.click();await expect(card.getByRole('button',{name:'Retry',exact:true})).toBeVisible();
 await card.getByRole('button',{name:'Close AI explanation'}).click();await trigger.click();await expect(card.getByRole('button',{name:'Retry',exact:true})).toBeVisible();expect(calls).toBe(2);
 const panel=page.locator('[aria-label="Reading questions"]'),before=await panel.evaluate(e=>e.scrollTop);
 await card.getByRole('button',{name:'Retry',exact:true}).evaluate(e=>{(e as HTMLButtonElement).click();(e as HTMLButtonElement).click();});
 await expect(card.getByRole('button',{name:'Show in passage'})).toBeVisible();expect(calls).toBe(3);expect(await panel.evaluate(e=>e.scrollTop)).toBe(before);
 await card.getByRole('button',{name:'Close AI explanation'}).click();await trigger.click();await expect(card.getByText('Saved explanation')).toBeVisible();expect(calls).toBe(3);
});
test('Reading multi-open, no-jump, exact navigation, verdict colors and reload cache',async({page},info)=>{
 const row=fixture.reading.positions[1];row.user_answer='synthetic wrong';fixture.answers[row.question_id]=row.user_answer;
 const radio=fixture.reading.positions.find((p:{number:number})=>p.number===8),wrong=fixture.reading.positions.find((p:{number:number})=>p.number===9);
 radio.user_answer=radio.correct_answer;radio.is_correct=true;radio.unanswered=false;fixture.answers[radio.question_id]=radio.user_answer;fixture.reading.raw_score=fixture.reading.positions.filter((p:{is_correct:boolean})=>p.is_correct).length;
 wrong.user_answer=wrong.correct_answer==='TRUE'?'FALSE':'TRUE';wrong.unanswered=false;fixture.answers[wrong.question_id]=wrong.user_answer;
 await loadReview(page,'reading');let generations=0;const saved=new Map<string,object>();
 await page.route('**/api/reading/review',async route=>{
  const qid=route.request().postDataJSON().question_id;let data=saved.get(qid);const cached=!!data;
  if(!data){generations++;const passage=fixture.readingExam.passages.find((p:{question_groups:{questions:{id:string}[]}[]})=>p.question_groups.some(g=>g.questions.some(q=>q.id===qid))),block=passage.content.findIndex((b:{type:string;text:string})=>b.type==='paragraph'&&b.text.length>100),text=passage.content[block].text;
   data={question_id:qid,fingerprint:'frozen-fixture',source_status:'needs_review',review:{why_user_answer_wrong:'Сохранённый ответ сопоставлен с ключом.',why_correct_answer_works:'Выбран контекст сохранённого текста.',ielts_tip:'Проверьте полный смысл вопроса.',evidence_status:'found',evidence:[{passage_id:passage.id,block_index:block,start:0,end:80,quote:text.slice(0,80),kind:'relevant_context'}]}};saved.set(qid,data);
  }await new Promise(r=>setTimeout(r,100));await route.fulfill({json:{...data,cached}});
 });
 const mobile=info.project.name.includes('mobile');if(mobile)await page.getByRole('button',{name:'Questions',exact:true}).click();
 const panel=page.locator('[aria-label="Reading questions"]'),first=page.getByRole('button',{name:'Explain question 1 with AI',exact:true}),card=page.getByRole('region',{name:'AI explanation for question 1',exact:true});
 // A normal click must reveal the response beside its own saved answer, rather
 // than silently appending it below the remaining questions in the group.
 await first.click();await expect(card.getByRole('button',{name:'Show in passage'})).toBeVisible();
 await expect(page.locator('[data-question="1"], [data-review-for="1"]')).toContainText('AI explanation');
 await card.getByRole('button',{name:'Close AI explanation'}).click();
 for(const top of [0,180,10000]){
  await panel.evaluate((e,n)=>e.scrollTop=n,top);const before=await panel.evaluate(e=>e.scrollTop);
  await first.evaluate(e=>(e as HTMLButtonElement).click());await expect(card.getByRole('button',{name:'Show in passage'})).toBeAttached();expect(await panel.evaluate(e=>e.scrollTop)).toBe(before);
  await card.getByRole('button',{name:'Close AI explanation'}).evaluate(e=>(e as HTMLButtonElement).click());expect(await panel.evaluate(e=>e.scrollTop)).toBe(before);
 }
 await first.evaluate(e=>(e as HTMLButtonElement).click());await page.getByRole('button',{name:'Explain question 2 with AI',exact:true}).evaluate(e=>(e as HTMLButtonElement).click());await expect(card).toBeAttached();await expect(page.getByRole('region',{name:'AI explanation for question 2',exact:true})).toBeAttached();
 await card.getByRole('button',{name:'Show in passage'}).evaluate(e=>(e as HTMLButtonElement).click());await expect(page.locator('[data-reading-ai="true"]').first()).toBeVisible();await page.getByRole('button',{name:/Back to Q1$/}).click();await expect.poll(()=>card.evaluate(e=>{const a=e.getBoundingClientRect(),b=e.closest('.questions-scroll')!.getBoundingClientRect();return a.top>=b.top&&a.top<b.bottom})).toBe(true);
 const q2=page.getByLabel('Answer 2',{exact:true});expect(await q2.evaluate(e=>getComputedStyle(e).color)).toBe('rgb(168, 62, 56)');
 await expect(page.locator('[data-question="9"] [aria-pressed="true"]')).toHaveAttribute('data-choice-status','incorrect');await expect(page.locator('[data-question="8"] [data-choice-status="correct"]')).toHaveCount(1);
 await expect(page.locator('[data-question="1"]')).toHaveAttribute('data-review-status','correct');await expect(page.locator('[data-question="3"]')).toHaveAttribute('data-review-status','unanswered');expect(await page.locator('.inline-question .answer-review').count()).toBe(0);
 mkdirSync(screenshots,{recursive:true});await page.screenshot({path:`${screenshots}/reading-${info.project.name}.png`});
 const count=generations;await page.reload();if(mobile)await page.getByRole('button',{name:'Questions',exact:true}).click();await first.click();await expect(card.getByText('Saved explanation')).toBeVisible();expect(generations).toBe(count);
});
test('Listening first-click, independent cards, dedup and own loop evidence',async({page},info)=>{
 for(const n of [1,3]){const q=fixture.listening.questions.find((q:{question_number:number})=>q.question_number===n);q.user_answer='synthetic wrong';q.correct=false;}
 await loadReview(page,'listening');const audioCount=await page.locator('audio').count();let calls=0;
 await page.route('**/api/listening/review',async route=>{calls++;const n=route.request().postDataJSON().question_number;await new Promise(r=>setTimeout(r,120));await route.fulfill({json:{cached:false,what_happened:`Вопрос ${n}.`,why:'Сравните сохранённый ответ.',next_time:'Проверьте ключ.',evidence:{available:true,reason:null,part:1,quote:'Synthetic fixture',segment_ids:['seg-0001'],clip_start:n,clip_end:n+1}}})});
 if(info.project.name.includes('mobile'))await page.getByRole('button',{name:'Questions',exact:true}).click();
 const q1=page.locator('#question-1'),q3=page.locator('#question-3'),a1=page.getByRole('region',{name:'AI explanation for question 1',exact:true}),a3=page.getByRole('region',{name:'AI explanation for question 3',exact:true});
 await q1.getByRole('button',{name:'Explain with AI'}).click();await q3.getByRole('button',{name:'Explain with AI'}).click();await expect(a1).toContainText('Вопрос 1.');await expect(a3).toContainText('Вопрос 3.');expect(calls).toBe(2);
 await q3.getByRole('button',{name:'Explain with AI'}).click();await expect(a1).toBeAttached();await expect(a3).toHaveCount(0);await q3.getByRole('button',{name:'Explain with AI'}).click();expect(calls).toBe(2);
 await a1.getByRole('button',{name:'Loop Moment'}).click();await expect(a1.getByRole('button',{name:'Loop Moment'})).toHaveAttribute('aria-pressed','true');await expect(a3.getByRole('button',{name:'Loop Moment'})).toHaveAttribute('aria-pressed','false');
 mkdirSync(screenshots,{recursive:true});await page.screenshot({path:`${screenshots}/listening-${info.project.name}.png`});expect(await page.locator('audio').count()).toBe(audioCount);
});
test('Translation exact selection, dedup, bounded reuse and meaningful failure messages',async({page},info)=>{
 await loadReview(page,'reading');
 await page.route('**/api/alua/reading/books',r=>r.fulfill({json:{items:[{exams:[{exam_id:fixture.readingExam.id,practice_policy_version:'private-practice-v1',enabled_for_private_practice:true,content_status:'needs_review'}]}]}}));
 await page.reload();if(info.project.name.includes('mobile'))await page.getByRole('button',{name:'Source',exact:true}).click();
 await page.getByRole('button',{name:'Translate',exact:true}).click();let status=429,calls=0;
 await page.route('**/api/translate',async route=>{calls++;await new Promise(r=>setTimeout(r,100));const body=route.request().postDataJSON();await route.fulfill({status,json:status===200?{expression:body.selected,translation:'контекст'}:{error:{code:status===429?'translate_rate_limited':status===504?'translate_timeout':'invalid_translation'}}})});
 const point=await page.locator('[data-highlight-block]').filter({hasText:'In Paris'}).first().evaluate(span=>{
  const panel=span.closest('.passage-scroll')!;panel.scrollTop+=span.getBoundingClientRect().top-panel.getBoundingClientRect().top-90;
  const walker=document.createTreeWalker(span,NodeFilter.SHOW_TEXT),node=walker.nextNode()!;const text=node.textContent!,word=/[A-Za-z]{4,}/.exec(text)!;const r=document.createRange();r.setStart(node,word.index);r.setEnd(node,word.index+word[0].length);const rect=r.getClientRects()[0]!;return {x:rect.x+rect.width/2,y:rect.y+rect.height/2};
 });
 await page.waitForTimeout(250);
 const card=page.getByRole('status',{name:'Перевод',exact:true});
 for(const [code,message]of [[429,'Подождите минуту'],[504,'слишком много времени'],[502,'точный перевод']] as const){status=code;await page.mouse.click(point.x,point.y);await expect(card).toContainText(message);await page.getByRole('button',{name:'Закрыть перевод'}).click();}
 status=200;const before=calls;await page.mouse.click(point.x,point.y);await page.mouse.click(point.x,point.y);await expect(card).toContainText('контекст');expect(calls-before).toBe(1);await page.getByRole('button',{name:'Закрыть перевод'}).click();await page.mouse.click(point.x,point.y);await expect(card).toContainText('контекст');expect(calls-before).toBe(1);
 mkdirSync(screenshots,{recursive:true});await page.screenshot({path:`${screenshots}/translation-${info.project.name}.png`});
});
test('Review radio, unordered set and inline sentence use saved verdict colors',async({page},info)=>{
 await page.goto('/ai-ux-fixture');
 const wrong=page.locator('[data-question="2"] label[data-choice-status="incorrect"]');expect(await wrong.evaluate(e=>getComputedStyle(e).color)).toBe('rgb(168, 62, 56)');
 const correct=page.locator('[data-question="1"] label[data-choice-status="correct"]');expect(await correct.evaluate(e=>getComputedStyle(e).color)).toBe('rgb(8, 127, 99)');
 await expect(page.locator('[data-question="3"] input:checked')).toHaveCount(0);
 await expect(page.locator('.multi-positions + fieldset [data-choice-status="correct"]')).toHaveCount(2);
 await expect(page.locator('.inline-question .answer-review')).toHaveCount(0);await expect(page.locator('[aria-label="Saved answers"] [data-review-for]')).toHaveCount(3);
 expect(await page.getByLabel('Answer 7',{exact:true}).evaluate(e=>getComputedStyle(e).color)).toBe('rgb(168, 62, 56)');
 mkdirSync(screenshots,{recursive:true});await page.screenshot({path:`${screenshots}/answer-semantics-${info.project.name}.png`,fullPage:true});
});
