import {test,expect} from "@playwright/test";
test.setTimeout(90000);
test.beforeEach(async({page})=>{await page.route("**/*",route=>{const url=new URL(route.request().url());if(url.protocol==="blob:")return route.continue();const host=url.hostname;if(!["127.0.0.1","localhost"].includes(host))return route.abort();return route.continue();});});
async function start(page:import("@playwright/test").Page,eid:string){await page.goto(`/listening/${Number(eid.split("-")[1])}/${eid}`);await page.getByRole("button",{name:"Start Listening",exact:true}).or(page.getByRole("link",{name:"Resume practice",exact:true})).click();await page.waitForURL(/\/listening\/attempts\/[\w-]+$/);await expect(page.getByLabel("Listening audio player")).toBeVisible();await page.getByRole("button",{name:"Go to question 1",exact:true}).click();}
async function showSource(page:import("@playwright/test").Page){const button=page.getByRole("button",{name:"Source material",exact:true});if(await button.isVisible())await button.click();}
async function showQuestions(page:import("@playwright/test").Page){const button=page.getByRole("button",{name:"Questions",exact:true});if(await button.isVisible())await button.click();}
async function time(page:import("@playwright/test").Page){return page.locator('audio').first().evaluate(el=>(el as HTMLAudioElement).currentTime);}
test("owned verified lifecycle, native audio, resume, transitions and review",async({page},info)=>{
 await page.goto('/listening');await expect(page.locator('main a[href*="cambridge-"]')).toHaveCount(72);
 await start(page,'cambridge-14-test-01');const url=page.url();await expect.poll(()=>page.locator("audio").first().evaluate(el=>(el as HTMLAudioElement).readyState)).toBeGreaterThan(0);await showSource(page);await expect.poll(()=>page.getByRole("button",{name:"Enlarge source image"}).first().locator("img").evaluate(el=>(el as HTMLImageElement).naturalWidth)).toBeGreaterThan(0);await page.screenshot({path:`.next/listening-workspace-${info.project.name}.png`});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);const player=page.getByRole('region',{name:'Listening audio player'});await expect(player.getByRole('button')).toHaveCount(3);await showQuestions(page);
 await page.getByRole('button',{name:'Play',exact:true}).click();await expect.poll(()=>time(page)).toBeGreaterThan(.2);
 await page.getByLabel('Question 1',{exact:true}).fill('Canadian');await page.getByLabel('Question 2',{exact:true}).fill('furniture');await expect(page.getByRole('button',{name:'Pause',exact:true})).toBeVisible();
 await page.getByLabel('Audio progress').fill('6');await page.getByRole('button',{name:'Pause',exact:true}).click();await page.getByRole('button',{name:'Back 5 seconds',exact:true}).click();expect(await time(page)).toBeLessThan(2);await page.getByRole('button',{name:'Forward 5 seconds',exact:true}).click();expect(await time(page)).toBeGreaterThan(5);
 await page.getByRole('button',{name:'Go to question 11',exact:true}).click();await expect(page.locator('#question-11')).toBeVisible();expect(await page.locator('audio').first().getAttribute('src')).toContain('/1');
 await page.locator('#question-11 input[type=radio]').first().check();await page.locator('#question-12 input[type=radio]').nth(2).check();
 await expect(page.getByRole('status').filter({hasText:/^Saved$/})).toBeVisible();await page.reload();await expect.poll(()=>time(page)).toBeGreaterThan(5);await expect(page.locator('#question-11 input[type=radio]').first()).toBeChecked();expect(await page.locator('audio').first().evaluate(el=>(el as HTMLAudioElement).paused)).toBe(true);
 await page.getByLabel('Audio part',{exact:true}).selectOption('2');await expect.poll(()=>page.locator('audio').first().getAttribute('src')).toContain('/2');
 await page.getByRole('button',{name:'Play',exact:true}).click();await expect.poll(()=>time(page)).toBeGreaterThan(.1);await page.getByLabel('Audio progress').fill('11.9');await expect(page.getByText('Cambridge 14 · Listening · Part 3 of 4')).toBeVisible({timeout:10000});
 await page.getByLabel('Audio part',{exact:true}).selectOption('4');await expect(page.getByText('Cambridge 14 · Listening · Part 4 of 4')).toBeVisible();
 await page.getByRole('button',{name:'Finish practice',exact:true}).click();await page.getByRole('button',{name:'Keep practising',exact:true}).click();await expect(page).toHaveURL(url);
 await page.getByRole('button',{name:'Finish practice',exact:true}).click();await page.getByRole('button',{name:'Finish and view results',exact:true}).click();await page.waitForURL(/\/results$/);await expect(page.getByText(/Estimated IELTS Band/)).toBeVisible();await expect(page.getByText('4 / 40',{exact:true})).toBeVisible();
 await page.getByRole('link',{name:'Review all questions'}).click();await expect(page.getByRole('heading',{name:'Review your answers'})).toBeVisible();await expect(page.getByText('Correct · Canadian',{exact:true})).toBeVisible();await expect(page.locator('input[aria-label="Question 1"]')).toBeDisabled();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await page.screenshot({path:`.next/listening-${info.project.name}.png`,fullPage:false});
});
test("preliminary, ungraded and source image viewer",async({page})=>{
 await start(page,'cambridge-21-test-01');await page.getByLabel('Question 1',{exact:true}).fill('10');await expect(page.getByRole('status').filter({hasText:/^Saved$/})).toBeVisible();await page.getByRole('button',{name:'Finish practice',exact:true}).click();await page.getByRole('button',{name:'Finish and view results',exact:true}).click();await page.waitForURL(/\/results$/);await expect(page.getByText('Preliminary result',{exact:true})).toBeVisible();await expect(page.getByText(/Estimated IELTS Band/)).toHaveCount(0);
 await start(page,'cambridge-04-test-02');await page.locator('#question-1 input[type=radio]').first().check();await expect(page.getByRole('status').filter({hasText:/^Saved$/})).toBeVisible();await page.getByRole('button',{name:'Finish practice',exact:true}).click();await page.getByRole('button',{name:'Finish and view results',exact:true}).click();await page.waitForURL(/\/results$/);await expect(page.getByText('Ungraded',{exact:true})).toBeVisible();await expect(page.getByText(/Estimated IELTS Band/)).toHaveCount(0);
 await start(page,'cambridge-14-test-02');await page.getByRole('button',{name:'Go to question 16',exact:true}).click();await page.getByRole('combobox',{name:'Question 16',exact:true}).selectOption('H');await showSource(page);const image=page.getByRole('button',{name:'Enlarge source image'}).first();await expect.poll(()=>image.locator("img").evaluate(el=>(el as HTMLImageElement).naturalWidth)).toBeGreaterThan(0);await image.click();await expect(page.getByRole('button',{name:'Close image'})).toBeVisible();await page.getByRole('button',{name:'Close image'}).click();expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
});
test("M4A, keyboard, retry and concurrent draft reconciliation",async({page})=>{
 await start(page,'cambridge-05-test-01');const id=page.url().split('/').pop()!;
 await expect.poll(()=>page.locator('audio').first().evaluate(el=>(el as HTMLAudioElement).readyState)).toBeGreaterThan(0);
 const head=await page.request.head(`/api/listening/audio/${id}/1`);expect(head.status()).toBe(200);expect(head.headers()['content-type']).toContain('audio/mp4');
 await page.getByRole('button',{name:'Play',exact:true}).click();await expect.poll(()=>time(page)).toBeGreaterThan(.1);await page.getByRole('button',{name:'Pause',exact:true}).click();
 await page.getByLabel('Audio progress').evaluate(el=>{const input=el as HTMLInputElement;Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value')!.set!.call(input,'6');input.dispatchEvent(new Event('input',{bubbles:true}));input.dispatchEvent(new Event('change',{bubbles:true}));});
 const input=page.getByLabel('Question 1',{exact:true});await input.focus();const before=await time(page);await page.keyboard.press('ArrowLeft');expect(Math.abs(await time(page)-before)).toBeLessThan(.2);
 await input.blur();await page.locator('main').click({position:{x:1,y:1}});await page.keyboard.press('Space');await expect.poll(()=>page.locator('audio').first().evaluate(el=>(el as HTMLAudioElement).paused)).toBe(false);await page.keyboard.press('Space');await expect.poll(()=>page.locator('audio').first().evaluate(el=>(el as HTMLAudioElement).paused)).toBe(true);
 await expect(page.getByRole('status').filter({hasText:/^Saved$/})).toBeVisible();
 const bodies:{event_id:string}[]=[];await page.route('**/api/alua/listening/attempts/*/sync',async route=>{bodies.push(route.request().postDataJSON());if(bodies.length===1)return route.abort();return route.continue();});
 await input.fill('first draft');await expect(page.getByRole('status').filter({hasText:/Offline or save interrupted/})).toBeVisible();await input.fill('newer local draft');await expect(page.getByRole('status').filter({hasText:/^Saved$/})).toBeVisible({timeout:20000});expect(bodies.length).toBeGreaterThan(1);expect(bodies[0]!.event_id).toBe(bodies[1]!.event_id);await page.unroute('**/api/alua/listening/attempts/*/sync');
 const headers={Authorization:`Bearer ${process.env.ALUA_LISTENING_TEST_TOKEN}`};const endpoint=`/api/alua/listening/attempts/${id}`;const remote=await (await page.request.get(endpoint,{headers})).json();expect(remote.answers['cambridge-05-test-01-q01']).toBe('newer local draft');
 expect((await page.request.post(endpoint+'/sync',{headers,data:{event_id:crypto.randomUUID(),expected_version:remote.version,answers:{...remote.answers,'cambridge-05-test-01-q01':'remote edit'},state:remote.state}})).ok()).toBe(true);
 await input.fill('local conflict');await page.getByRole('button',{name:'Keep my local answers'}).click();await expect(page.getByRole('status').filter({hasText:/^Saved$/})).toBeVisible();await page.reload();await expect(page.getByLabel('Question 1',{exact:true})).toHaveValue('local conflict');
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
 await page.getByRole('button',{name:'Go to question 11',exact:true}).click();
 await showSource(page);await expect(source.getByText('Answer bank',{exact:true})).toBeVisible();
 await expect(source.getByText('Questions 11–12',{exact:true})).toBeVisible();
 // One scroll gesture can cross several groups (including touch momentum).
 await showQuestions(page);await questions.dispatchEvent('wheel',{deltaY:1000});
 await questions.evaluate(el=>{const next=el.querySelectorAll('[data-question-group]')[1]!;el.scrollTop+=next.getBoundingClientRect().top-el.getBoundingClientRect().top-20;});
 await expect(source.locator('header span')).toHaveText('Questions 13–14');
 await questions.evaluate(el=>{el.scrollTop=el.scrollHeight;});
 await expect(source.locator('header span')).toHaveText('Questions 15–20');
 await page.getByRole('button',{name:'Go to question 15',exact:true}).click();
 await expect(questions).toBeVisible();await showSource(page);
 await expect(source.getByText('Questions 15–20',{exact:true})).toBeVisible();
 expect(await page.locator('audio').first().getAttribute('src')).toContain('/1');
 // A structured group occupies the full workspace, including the bank when present.
 await start(page,'cambridge-14-test-02');await expect(source).toHaveCount(0);
 await expect(questions).toBeVisible();
 expect(await questions.evaluate(el=>el.parentElement!.children.length)).toBe(1);
 await page.getByRole('button',{name:'Go to question 16',exact:true}).click();
 await showSource(page);await expect(source).toBeVisible();
 await expect(source.getByText('Questions 16–20',{exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Go to question 11',exact:true}).click();
 await expect(source).toHaveCount(0);await expect(questions).toBeVisible();
 await page.getByRole('button',{name:'Go to question 25',exact:true}).click();
 await expect(source).toHaveCount(0);await expect(questions.getByText('Answer bank',{exact:true})).toBeVisible();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 expect(await page.evaluate(()=>document.documentElement.scrollHeight<=innerHeight+1)).toBe(true);
 await page.screenshot({path:`.next/listening-adaptive-${info.project.name}.png`});
});
