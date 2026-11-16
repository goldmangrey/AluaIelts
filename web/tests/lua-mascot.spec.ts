import {expect,test} from '@playwright/test';
import {resolve} from 'node:path';
import {fixture,attemptId,loadReview} from './review-focus-fixture';
const output=resolve('../work/lua-mascot');
const mascot='[data-lua-context="hero"] > span';
const empty={items:[],total:0,page:1,limit:20};
test('responsive hero, decoded layers, blink, pause, reduced motion and no layout shift',async({page,context})=>{
  await page.addInitScript(()=>localStorage.setItem('lua-test-guest','1'));
  const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/api/alua/**',r=>r.fulfill({json:empty}));
  await page.goto('/');await expect(page.locator(mascot)).toHaveAttribute('data-lua-active','true');
  const hero=page.locator('section[aria-labelledby="home-title"]');
  for(const width of [1440,1280,390,375,320]){
    await page.setViewportSize({width,height:width>600?1000:844});
    await page.evaluate(()=>document.fonts.ready);
    expect(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)).toBe(false);
    const h=await hero.boundingBox();expect(h!.height).toBeLessThan(560);
    await expect(page.locator('nav[aria-label="IELTS sections"] a')).toHaveCount(4);
    // Lua must not cover any visible text, including the typewriter's reserved box.
    const overlaps=await hero.evaluate(el=>{
      const image=el.querySelector('[data-lua-context="hero"] > span')!.getBoundingClientRect();
      // The raster's visible bounds are 14–88% horizontally, 6–88% vertically.
      const a={left:image.left+image.width*.14,right:image.left+image.width*.88,top:image.top+image.height*.06,bottom:image.top+image.height*.88};
      return [...el.querySelectorAll('h1,h2,p')].filter(n=>{const b=n.getBoundingClientRect();return a.left<b.right&&a.right>b.left&&a.top<b.bottom&&a.bottom>b.top;}).map(n=>n.textContent);
    });expect(overlaps).toEqual([]);
    await page.screenshot({path:`${output}/home-${width}.png`,fullPage:true});
  }
  await page.setViewportSize({width:1440,height:1000});const before=(await hero.boundingBox())!.height;
  await page.locator(mascot).evaluate(el=>new Promise<void>((done,reject)=>{const timer=setTimeout(()=>{observer.disconnect();reject(Error('No blink in 8 seconds'));},8000);const observer=new MutationObserver(()=>{if(el.hasAttribute('data-lua-blink')){clearTimeout(timer);observer.disconnect();done();}});observer.observe(el,{attributes:true,attributeFilter:['data-lua-blink']});}));
  await page.locator(mascot).screenshot({path:`${output}/blink.png`});
  await expect(page.locator(mascot)).not.toHaveAttribute('data-lua-blink','true');
  expect((await hero.boundingBox())!.height).toBe(before);
  await page.setViewportSize({width:1440,height:500});
  await page.evaluate(()=>scrollTo(0,document.documentElement.scrollHeight));
  await expect(page.locator(mascot)).toHaveAttribute('data-lua-active','false');
  await page.evaluate(()=>scrollTo(0,0));await page.setViewportSize({width:1440,height:1000});await expect(page.locator(mascot)).toHaveAttribute('data-lua-active','true');
  // Actual background tab state, when the browser exposes it in headless mode.
  const tab=await context.newPage();await tab.goto('about:blank');await tab.bringToFront();
  if(await page.evaluate(()=>document.hidden))await expect(page.locator(mascot)).toHaveAttribute('data-lua-active','false');
  await tab.close();await page.bringToFront();await expect(page.locator(mascot)).toHaveAttribute('data-lua-active','true');
  await page.emulateMedia({reducedMotion:'reduce'});await expect(page.locator(mascot)).toHaveAttribute('data-lua-active','false');
  const animation=await page.locator(mascot).evaluate(el=>[...el.querySelectorAll('span')].map(n=>getComputedStyle(n).animationName));
  expect(animation.every(n=>n==='none')).toBe(true);
  await page.screenshot({path:`${output}/reduced-motion.png`});
  await page.emulateMedia({reducedMotion:'no-preference'});await expect(page.locator(mascot)).toHaveAttribute('data-lua-active','true');
  for(const skill of ['listening','reading','writing','speaking']){await page.goto('/');await expect(page.locator(mascot)).toHaveAttribute('data-lua-active','true');await page.locator(`nav[aria-label="IELTS sections"] a[href="/${skill}"]`).click();await expect(page).toHaveURL(new RegExp(`/${skill}$`));}
  expect(errors).toEqual([]);
});

for(const section of ['listening','reading'] as const)test(`${section}: saved lookup has no Thinking, new generation has Thinking, reopening makes no POST`,async({page})=>{
  await loadReview(page,section);
  const exam=fixture.readingExam,q=exam.passages.flatMap((p:{question_groups:{questions:{id:string}[]}[]})=>p.question_groups.flatMap(g=>g.questions))[1];
  const question=page.locator(section==='listening'?'#question-2':'[data-question="2"]');
  const data=section==='listening'?{what_happened:'Saved source comparison.',why:'Read the final detail.',next_time:'Check the final detail.',evidence:{available:false,reason:null,part:1,quote:null,segment_ids:[],clip_start:null,clip_end:null}}:{question_id:q.id,fingerprint:'fixture',source_status:'ready',review:{why_user_answer_wrong:'Compare the detail.',why_correct_answer_works:'The passage confirms the detail.',ielts_tip:'Read the context.',evidence_status:'found',evidence:[{passage_id:exam.passages[0].id,block_index:0,start:0,end:12,quote:exam.passages[0].content[0].text.slice(0,12),kind:'support'}]}};
  let saved=false,posts=0,releaseLookup:(()=>void)|undefined,releaseGeneration:(()=>void)|undefined;
  await page.route(`**/api/alua/practice/reviews/${section}/**`,async route=>{
    if(!new URL(route.request().url()).searchParams.has('question')){await route.fulfill({json:{questions:[]}});return;}
    if(!saved)await new Promise<void>(done=>{releaseLookup=done;});
    await route.fulfill({json:{response:saved?data:null}});
  });
  await page.route(`**/api/${section}/review`,async route=>{posts++;await new Promise<void>(done=>{releaseGeneration=done;});saved=true;await route.fulfill({json:data});});
  await question.getByRole('button',{name:/Explain.*with AI/}).click();
  await expect.poll(()=>!!releaseLookup).toBe(true);
  await expect(page.locator('img[src$="thinking.webp"]')).toHaveCount(0);
  releaseLookup!();await expect(page.locator('img[src$="thinking.webp"]')).toBeVisible();
  await expect.poll(()=>!!releaseGeneration).toBe(true);releaseGeneration!();
  await expect(page.locator('img[src$="aha.webp"]')).toBeVisible();
  await page.screenshot({path:`${output}/${section}-ai-saved.png`});
  await question.getByRole('button',{name:/Explain.*with AI|View AI [Ee]xplanation/}).click();
  await question.getByRole('button',{name:/Explain.*with AI|View AI [Ee]xplanation/}).click();
  await expect(page.locator('img[src$="aha.webp"]')).toBeVisible();
  await expect(page.locator('img[src$="thinking.webp"]')).toHaveCount(0);expect(posts).toBe(1);
  await page.reload();
  await question.getByRole('button',{name:/Explain.*with AI|View AI [Ee]xplanation/}).click();
  await expect(page.locator('img[src$="aha.webp"]')).toBeVisible();expect(posts).toBe(1);
});

test('History sleepy only in empty In Progress, detail support/wink only after successful save',async({page})=>{
  let draft=false,fail=true;
  const item={module:'writing',attempt_id:attemptId,item_key:'grammar-1',title:'Grammar feedback',number:null,category:'grammar',completed_at:null,answer:'Sample',correct_answer:null,feedback:null,reviewed:false,review_key:null,has_saved_review:false,saved_review:null,href:'/writing'};
  await page.route('**/api/alua/**',route=>{
    const path=new URL(route.request().url()).pathname;
    if(route.request().method()==='PUT')return route.fulfill({status:fail?500:200,json:{}});
    return route.fulfill({json:path.includes('/mistakes')?{...empty,items:[item],total:1}:path.includes('/drafts')&&draft?{...empty,items:[{id:attemptId,module:'reading',title:'Draft',href:'/reading',answered:2,position:'Passage 1'}],total:1}:empty});
  });
  await page.goto('/practice/history');await expect(page.locator('img[src$="sleepy.webp"]')).toHaveCount(0);
  await page.getByRole('button',{name:'In Progress',exact:true}).click();await expect(page.locator('img[src$="sleepy.webp"]')).toBeVisible();
  await page.screenshot({path:`${output}/history-empty.png`});
  draft=true;await page.reload();await page.getByRole('button',{name:'In Progress',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Draft',exact:true})).toBeVisible();await expect(page.locator('img[src$="sleepy.webp"]')).toHaveCount(0);
  await page.goto('/practice/mistakes');await expect(page.locator('img[src$="support.webp"]')).toHaveCount(0);
  await page.getByRole('link',{name:/Grammar feedback/}).click();await expect(page.locator('img[src$="support.webp"]')).toBeVisible();
  await page.getByRole('button',{name:'Mark as reviewed',exact:true}).click();await expect(page.getByRole('alert')).toBeVisible();await expect(page.locator('img[src$="wink.webp"]')).toHaveCount(0);
  fail=false;await page.getByRole('button',{name:'Mark as reviewed',exact:true}).click();await expect(page.locator('img[src$="wink.webp"]')).toBeVisible();
  await page.screenshot({path:`${output}/mistake-reviewed.png`});await expect(page.locator('img[src$="support.webp"]')).toBeVisible({timeout:4000});
});

for(const section of ['listening','reading'] as const)test(`${section}: celebration preserves actual result and band at 0 and 30`,async({page})=>{
  let score=30;
  await page.route('**/api/alua/**',route=>{
    const path=new URL(route.request().url()).pathname,isReading=section==='reading',result=structuredClone(fixture[section]);
    if(isReading){result.raw_score=score;result.estimated_band=score?7:null;result.positions.forEach((p:{is_correct:boolean;unanswered:boolean},i:number)=>{p.is_correct=i<score;p.unanswered=false;});}
    else {result.correct_count=score;result.graded_count=40;result.estimated_band=score?7:null;result.questions.forEach((p:{correct:boolean;user_answer:string},i:number)=>{p.correct=i<score;p.user_answer='fixture';});}
    result.attempt_id=attemptId;
    return route.fulfill({json:path.endsWith('/review')||path.endsWith('/result')?result:{id:attemptId,exam_id:fixture.readingExam.id,content_hash:result.content_hash,status:'submitted',mode:'full_exam',version:1,server_now:new Date().toISOString(),deadline_at:new Date(Date.now()+3600000).toISOString(),not_fully_proofread:true,answers:{},state:{current_passage:1,checked_question_ids:[]},exam:fixture.readingExam}});
  });
  for(const value of [30,0]){
    score=value;await page.goto(`/${section}/attempts/${attemptId}/${section==='reading'?'result':'results'}`);
    await expect(page.getByLabel('Correct answers score',{exact:true})).toHaveText(`${value}/40`);
    await expect(page.getByLabel('Estimated IELTS band score',{exact:true})).toHaveText(value?'7.0':'Not available');
    await expect(page.locator('img[src$="celebration.webp"]')).toBeVisible();
    await page.setViewportSize({width:390,height:844});
    expect(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)).toBe(false);
    await page.screenshot({path:`${output}/${section}-result-${value}.png`,fullPage:true});
  }
});

test('catalog companions, real draft condition and positive streak condition',async({page})=>{
  let draft=false,streak=3;
  const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/api/alua/**',route=>{
    const path=new URL(route.request().url()).pathname;
    const json=path.endsWith('/me')?{uid:'review-fixture',display_name:'QA learner',email:null,target_ielts_band:7}:path.endsWith('/activity')?{current_streak:streak,total_practice_sessions:3,longest_streak:3,active_days:3,undated_sessions:0,days:Array.from({length:365},(_,i)=>({date:new Date(Date.UTC(2025,10,17+i)).toISOString().slice(0,10),count:i>361?1:0}))}:path.endsWith('/analytics')?{counts:{listening:0,reading:0,writing:0,speaking:0},charts:{},weak_areas:[],writing_criteria:[],mistakes:{total:0,reviewed:0}}:path.includes('/drafts')&&draft?{...empty,items:[{id:attemptId,module:'reading',title:'Real draft',href:'/reading',answered:2,position:'Passage 1',updated_at:new Date().toISOString(),deadline_at:null}],total:1}:path.endsWith('/listening/exams')?{items:Array.from({length:72},(_,i)=>({book:Math.floor(i/4)+4,exam_id:`test-${i}`,printed_test_number:i%4+1,active_attempt_id:null,audio:{technically_available:true}}))}:path.endsWith('/reading/books')?{dataset_version:'fixture',items:[]}:empty;
    return path.endsWith('/avatar')?route.fulfill({status:404}):route.fulfill({json});
  });
  for(const [route,emotion] of [['listening','listening'],['reading','scholar']] as const){
    await page.goto(`/${route}`);await expect(page.locator(`img[src$="${emotion}.webp"]`)).toBeVisible();
    await page.setViewportSize({width:390,height:844});await page.screenshot({path:`${output}/${route}-catalog.png`,fullPage:true});
  }
  await page.goto('/practice/continue');await expect(page.locator('img[src$="happy.webp"]')).toHaveCount(0);
  draft=true;await page.reload();await expect(page.locator('img[src$="happy.webp"]')).toBeVisible();
  await page.screenshot({path:`${output}/continue-draft.png`,fullPage:true});
  await page.goto('/');await expect(page.getByRole('heading',{name:'Real draft'})).toBeVisible();
  await expect(page.locator('[data-lua-context="continue"]')).toBeVisible();
  await expect(page.locator('#home-title')).toHaveCount(0);
  await expect(page.locator('#lua-message-title')).toBeVisible();
  await page.goto('/profile');await expect(page.locator('img[src$="proud.webp"]')).toBeVisible();
  await page.screenshot({path:`${output}/profile-streak.png`,fullPage:true});
  streak=0;await page.reload();await expect(page.getByText('Study Streak',{exact:true})).toBeVisible();await expect(page.locator('img[src$="proud.webp"]')).toHaveCount(0);
  expect(errors).toEqual([]);
});
