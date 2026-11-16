import {test,expect,type Page} from '@playwright/test';
import {readFileSync,mkdirSync} from 'node:fs';
import {resolve} from 'node:path';
import {releaseBackend,exam as readingExam,attemptId} from './reading-release-fixture';
const listeningExam=JSON.parse(readFileSync(resolve('../backend/app/content/listening_v1/exams/cambridge-04-test-01.json'),'utf8'));
const eid=listeningExam.exam_id;
const shots=resolve('../work/test-start-modal');mkdirSync(shots,{recursive:true});
async function stub(page:Page,{active=false}={}){
 const backend=await releaseBackend(page.context(),{existing:active});let creates=0;
 await page.route(`**/api/alua/reading/exams/${readingExam.id}`,route=>route.fulfill({json:readingExam}));
 const entry={exam_id:eid,book:4,printed_test_number:1,local_ordinal:1,content_mode:'preliminary',can_start:true,block_reason:null,question_count:40,renderable_count:40,active_attempt_id:active?attemptId:null,answered_count:active?6:0,completed_count:0,audio:{technically_available:true,available_parts:[1,2,3,4],decode_verified_parts:0,content_mapping_verified_parts:0}};
 await page.route('**/api/alua/listening/**',async route=>{
  const path=new URL(route.request().url()).pathname;
  if(path.endsWith('/exams'))return route.fulfill({json:{items:Array.from({length:72},(_,i)=>({...entry,exam_id:i===0?eid:`cambridge-${String(4+Math.floor(i/4)).padStart(2,'0')}-test-0${i%4+1}`,book:4+Math.floor(i/4),printed_test_number:i%4+1}))}});
  if(path.endsWith(`/exams/${eid}`))return route.fulfill({json:{exam:listeningExam,metadata:entry}});
  if(path.endsWith('/attempts')&&route.request().method()==='POST'){creates++;expect(route.request().postDataJSON().reuse_active).toBe(true);return route.fulfill({json:{id:attemptId,exam_id:eid}});}
  return route.fulfill({status:404,json:{error:{code:'fixture_not_found'}}});
 });
 // Keep navigation assertions isolated from exam/editor side effects.
 await page.route('**/listening/attempts/**',route=>route.request().resourceType()==='document'?route.fulfill({contentType:'text/html',body:'<main>Existing Listening workspace</main>'}):route.continue());
 return {backend,creates:()=>creates};
}
for(const skill of ['Reading','Listening'] as const){
 const path=skill==='Reading'?'/reading/cambridge-18':'/listening';
 const id=skill==='Reading'?readingExam.id:eid;
 test(`${skill}: metadata, focus, history, refresh, direct URL, responsive screenshots`,async({page},info)=>{
  const {backend,creates}=await stub(page);const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
  await page.setViewportSize({width:390,height:360});await page.goto(path);const link=page.locator(`a[href="?test=${id}"]`);await link.scrollIntoViewIfNeeded();await link.focus();const scroll=await page.evaluate(()=>scrollY);await link.click();
  const dialog=page.getByRole('dialog',{name:`Ready for ${skill}?`});await expect(dialog).toBeVisible();await expect(dialog.getByRole('button',{name:`Start ${skill}`,exact:false})).toBeVisible();
  expect(backend.events.length+creates()).toBe(0);
  await page.keyboard.press('Escape');await expect(dialog).toHaveCount(0);await expect(link).toBeFocused();expect(await page.evaluate(()=>scrollY)).toBe(scroll);
  await link.click();await page.goBack();await expect(dialog).toHaveCount(0);await page.goForward();await expect(dialog).toBeVisible();
  await page.reload();await expect(dialog).toBeVisible();await expect(dialog.getByText(skill==='Reading'?'Minutes':'Parts',{exact:true})).toBeVisible();
  for(const width of [1440,1280,430,390,375,320]){
   await page.setViewportSize({width,height:width<500?740:950});await expect(dialog).toBeVisible();
   expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
   const box=await dialog.boundingBox();expect(box!.x).toBeGreaterThanOrEqual(0);expect(box!.y).toBeGreaterThanOrEqual(0);expect(box!.x+box!.width).toBeLessThanOrEqual(width);
   await dialog.getByRole('button',{name:`Start ${skill}`,exact:false}).focus();
   await page.keyboard.press('Tab');expect(await dialog.evaluate(el=>el.contains(document.activeElement))).toBe(true);
   await dialog.evaluate(el=>Promise.all(el.getAnimations().map(a=>a.finished)));
   if(info.project.name.endsWith('chromium'))await page.screenshot({path:resolve(shots,`${skill.toLowerCase()}-${width}.png`)});
  }
  await page.setViewportSize({width:320,height:360});await dialog.getByRole('button',{name:`Start ${skill}`,exact:false}).scrollIntoViewIfNeeded();await expect(dialog.getByRole('button',{name:`Start ${skill}`,exact:false})).toBeInViewport();
  await dialog.getByRole('button',{name:'Close test details'}).click();await expect(dialog).toHaveCount(0);
  await expect(page).toHaveURL(new RegExp(`${path}$`));
  expect(backend.events.length+creates()).toBe(0);expect(errors).toEqual([]);
 });
 test(`${skill}: direct preparation URL restores catalog modal`,async({page})=>{
  await stub(page);await page.goto(skill==='Reading'?`${path}/${id}`:`/listening/4/${id}`);
  await expect(page.getByRole('dialog',{name:`Ready for ${skill}?`})).toBeVisible();
  await expect(page).toHaveURL(new RegExp(`\\?test=${id}$`));
 });
 test(`${skill}: double Start creates once; Continue creates nothing`,async({page})=>{
  const {backend,creates}=await stub(page);await page.goto(`${path}?test=${id}`);
  const button=page.getByRole('button',{name:`Start ${skill}`,exact:false});await expect(button).toBeEnabled();
  await button.evaluate(el=>{(el as HTMLButtonElement).click();(el as HTMLButtonElement).click();});
  await expect(page).toHaveURL(new RegExp(`/${skill.toLowerCase()}/attempts/${attemptId}`));
  expect(skill==='Reading'?backend.events.filter(e=>e.path==='/reading/attempts').length:creates()).toBe(1);
 });
 test(`${skill}: existing attempt is continued`,async({page})=>{
  const {backend,creates}=await stub(page,{active:true});await page.goto(`${path}?test=${id}`);
  await page.getByRole(skill==='Reading'?'button':'link',{name:`Continue ${skill}`,exact:false}).click();
  await expect(page).toHaveURL(new RegExp(`/${skill.toLowerCase()}/attempts/${attemptId}`));expect(backend.events.length+creates()).toBe(0);
 });
 test(`${skill}: guest returns to selected test without creating an attempt`,async({page})=>{
  const {backend,creates}=await stub(page);await page.addInitScript(()=>localStorage.setItem('release-signed-out','1'));
  await page.goto(`${path}?test=${id}`);const dialog=page.getByRole('dialog',{name:`Ready for ${skill}?`});await expect(dialog).toBeVisible();
  await dialog.getByRole('button',{name:`Start ${skill}`,exact:false}).click();await expect(dialog.getByRole('button',{name:'Continue with Google'})).toBeVisible();
  const target=new URL((await dialog.getByRole('link',{name:'More sign-in options'}).getAttribute('href'))!,'http://localhost');expect(target.searchParams.get('next')).toBe(`${path}?test=${id}`);
  expect(backend.events.length+creates()).toBe(0);
  for(const width of [390,320]){
   await page.setViewportSize({width,height:640});
   expect(await dialog.evaluate(el=>el.scrollWidth<=el.clientWidth)).toBe(true);
   await dialog.getByRole('button',{name:'Continue with Google'}).scrollIntoViewIfNeeded();
   await expect(dialog.getByRole('button',{name:'Continue with Google'})).toBeInViewport();
  }
  await dialog.getByRole('button',{name:'Not now'}).click();await expect(dialog.getByRole('button',{name:`Start ${skill}`,exact:false})).toBeVisible();
  await page.keyboard.press('Escape');await expect(dialog).toHaveCount(0);
 });
}
