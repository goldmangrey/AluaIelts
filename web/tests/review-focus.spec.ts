import { test, expect } from "@playwright/test";
import { mkdirSync, writeFileSync } from "node:fs";
import { loadReview } from "./review-focus-fixture";
for (const section of ["listening","reading"] as const) test(`${section}: focused review`,async({page},info)=>{
  const {assets,mutations}=await loadReview(page,section);
  const baseline=process.env.ALUA_FOCUS_BASELINE==="1";
  const measurements=await page.evaluate((section)=>{
    const workspace=document.querySelector(section==="listening"?'[data-layout]':'.exam-workspace')!.getBoundingClientRect();
    const player=document.querySelector('[aria-label="Listening audio player"]')?.getBoundingClientRect();
    const header=document.querySelector(section==="listening"?'main header>div':'.exam-header')!.getBoundingClientRect();
    return {workspace:workspace.height,top:workspace.top,header:header.height,player:player?.height??0,bottom:document.querySelector('main footer')?.getBoundingClientRect().height??0};
  },section);
  mkdirSync("docs/review-focus-v2",{recursive:true});
  writeFileSync(`docs/review-focus-v2/${baseline?"before":"after"}-${section}-${info.project.name}.json`,JSON.stringify(measurements,null,2));
  if(baseline)return;
  expect(measurements.header).toBe(48);expect(measurements.bottom).toBe(0);
  if(section==="listening"){expect(measurements.player).toBeGreaterThanOrEqual(90);expect(measurements.player).toBeLessThanOrEqual(105);}
  expect(await page.evaluate(()=>({x:document.documentElement.scrollWidth>innerWidth,y:document.documentElement.scrollHeight>innerHeight}))).toEqual({x:false,y:false});
  await expect(page.getByRole('heading',{name:'Review your answers'})).toHaveCount(0);
  await expect(page.locator('main footer')).toHaveCount(0);
  const screenshots=info.project.name.endsWith("-1366")||info.project.name.endsWith("-375")?"docs/review-focus-v2":".next/review-focus-screenshots";
  await page.screenshot({path:`${screenshots}/${section}-${info.project.name}.png`,scale:"css"});
  const mobile=page.viewportSize()!.width<700;
  const source=page.locator(section==="listening"?'[aria-label="Listening source material"]':'[aria-label="Reading passage"]');
  const answers=page.locator(section==="listening"?'[aria-label="Listening questions"]':'[aria-label="Reading questions"]');
  async function showSource(){if(mobile)await page.getByRole("button",{name:section==="listening"?"Source material":"Source",exact:true}).click();}
  async function showQuestions(){if(mobile)await page.getByRole("button",{name:"Questions",exact:true}).click();}
  async function part(n:number){await page.getByRole("button",{name:new RegExp(`^${section==="listening"?"Part":"Passage"} ${n}`)}).click();}
  await showSource();await expect(source).toBeVisible();
  if(section==="listening"){
    await expect.poll(()=>source.locator("img").first().evaluate(el=>(el as HTMLImageElement).naturalWidth)).toBeGreaterThan(0);
    await expect(page.locator('[data-waveform-source="audio"]')).toBeVisible();
  }
  await source.evaluate(el=>{el.scrollTop=180;});const sourceOffset=await source.evaluate(el=>el.scrollTop);
  await showQuestions();await answers.evaluate(el=>{el.scrollTop=160;});const questionOffset=await answers.evaluate(el=>el.scrollTop);
  if(!mobile)expect(await source.evaluate(el=>el.scrollTop)).toBe(sourceOffset);
  // Existing per-Part/Passage positions and prepared images survive a round trip.
  await part(2);await part(1);await showSource();
  await expect.poll(()=>source.evaluate(el=>el.scrollTop)).toBe(sourceOffset);
  await showQuestions();await expect.poll(()=>answers.evaluate(el=>el.scrollTop)).toBe(questionOffset);
  await part(2);await showSource();
  if(section==="listening")await expect.poll(()=>source.locator("img").first().evaluate(el=>(el as HTMLImageElement).naturalWidth)).toBeGreaterThan(0);
  await part(1);await showSource();
  const prepared=[...assets];await part(2);await part(1);
  await showQuestions();expect(assets).toEqual(prepared);
  const divider=page.getByRole("separator");
  if(!mobile){await divider.focus();await page.keyboard.press("ArrowRight");await expect(divider).toHaveAttribute("aria-valuenow","57");await page.keyboard.press("ArrowLeft");}
  await page.getByRole("navigation",{name:"Review filters"}).getByRole("button",{name:/^Incorrect/}).click();
  await expect(page.locator(section==="listening"?'#question-2':'[data-question="2"]')).toBeVisible();
  await expect(page.locator(section==="listening"?'#question-1':'[data-question="1"]')).toBeHidden();
  await page.getByRole("navigation",{name:"Review filters"}).getByRole("button",{name:/^Unanswered/}).click();
  await expect(page.locator(section==="listening"?'#question-3':'[data-question="3"]')).toBeVisible();
  await page.getByRole("navigation",{name:"Review filters"}).getByRole("button",{name:"All",exact:true}).click();
  await page.getByRole("button",{name:"Question navigator",exact:true}).click();
  const dialog=page.getByRole("dialog",{name:section==="listening"?"Questions":"All questions",exact:true});
  await expect(dialog).toBeVisible();
  const numbers=dialog.locator('button[data-review-status]');await expect(numbers).toHaveCount(40);
  await expect(numbers.nth(0)).toHaveAttribute("data-review-status","correct");await expect(numbers.nth(1)).toHaveAttribute("data-review-status","incorrect");await expect(numbers.nth(2)).toHaveAttribute("data-review-status","unanswered");
  await numbers.nth(39).click();await expect(dialog).toBeHidden();
  await expect(page.locator(section==="listening"?'#question-40':'[data-question="40"]')).toBeInViewport();
  const target=await page.locator(section==="listening"?'#question-40':'[data-question="40"]').boundingBox();
  const filterBounds=await page.getByRole("navigation",{name:"Review filters"}).boundingBox();
  expect(target!.y).toBeGreaterThanOrEqual(filterBounds!.y+filterBounds!.height-1);
  await page.getByRole("button",{name:"Question navigator",exact:true}).click();
  await numbers.nth(1).click();
  await expect(page.locator(section==="listening"?'#question-2':'[data-question="2"]')).toBeInViewport();
  if(section==="listening"){
    const question=page.locator("#question-2");await question.getByRole("button",{name:"Explain with AI",exact:true}).click();
    const ai=page.getByRole("region",{name:"AI explanation for question 2"});await expect(ai).toContainText("Check the final detail.");
    await ai.getByRole("button",{name:"Play Moment",exact:true}).click();
    await expect.poll(()=>page.locator("audio").first().evaluate(el=>(el as HTMLAudioElement).paused)).toBe(false);
    await expect.poll(()=>page.locator("audio").first().evaluate(el=>(el as HTMLAudioElement).paused)).toBe(true);
    await ai.getByRole("button",{name:"Loop Moment",exact:true}).click();
    await expect(ai.getByRole("button",{name:"Loop Moment"})).toHaveAttribute("aria-pressed","true");
    await page.locator('audio').first().evaluate(el=>{el.setAttribute('data-loop-seeks','0');el.addEventListener('seeked',()=>{if((el as HTMLAudioElement).currentTime<1.2)el.setAttribute('data-loop-seeks',String(Number(el.getAttribute('data-loop-seeks'))+1));});});
    await expect.poll(()=>page.locator('audio').first().getAttribute('data-loop-seeks')).toMatch(/^[2-9]/);
    await ai.getByRole("button",{name:"Loop Moment",exact:true}).click();
    await expect.poll(()=>page.locator("audio").first().evaluate(el=>(el as HTMLAudioElement).paused)).toBe(true);
    await question.getByRole("button",{name:"Explain with AI",exact:true}).click();await expect(ai).toHaveCount(0);
    await expect(page.locator("#question-3").getByRole("button",{name:"Explain with AI",exact:true})).toHaveCount(0);
    await expect(page.locator('main input:not([type="range"]),main select,main textarea')).toHaveCount(0);
    await page.getByRole("button",{name:"Play",exact:true}).click();
    await expect.poll(()=>page.locator("audio").first().evaluate(el=>(el as HTMLAudioElement).currentTime)).toBeGreaterThan(.1);
    await page.getByRole("button",{name:"Pause",exact:true}).click();
    await page.getByLabel("Audio progress").fill("6");await page.getByRole("button",{name:"Back 5 seconds"}).click();
    expect(await page.locator("audio").first().evaluate(el=>(el as HTMLAudioElement).currentTime)).toBeLessThan(2);
    await page.getByRole("button",{name:"Forward 5 seconds"}).click();
    expect(await page.locator("audio").first().evaluate(el=>(el as HTMLAudioElement).currentTime)).toBeGreaterThan(5);
    await part(2);await expect(page.locator("audio").first()).toHaveAttribute("src",/\/1$/);
    await page.getByRole("button",{name:"Listen to Part 2",exact:true}).click();await expect(page.locator("audio").first()).toHaveAttribute("src",/\/2$/);
  } else {
    await expect(page.locator(".answer-review").filter({hasText:"Your answer: wrong"})).toContainText("Correct answer:");
    expect(await page.locator('main input,main select,main textarea').evaluateAll(els=>els.every(el=>(el as HTMLInputElement).disabled))).toBe(true);
  }
  await page.screenshot({path:`${screenshots}/${section}-${info.project.name}-questions.png`,scale:"css"});
  expect(mutations).toEqual([]);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth&&document.documentElement.scrollHeight<=innerHeight)).toBe(true);
});
