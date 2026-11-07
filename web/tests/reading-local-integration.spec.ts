import {test,expect} from "@playwright/test";
// No API route mocks. The Python runner owns a disposable PostgreSQL cluster and
// genuine FastAPI HTTP server; only browser sign-in uses an isolated test identity.
test("real local FastAPI + PostgreSQL lifecycle through Next proxy, grading, review and history",async({page})=>{
 const started=Date.now();
 const outside:string[]=[];page.on("request",r=>{if(!r.url().startsWith("blob:")&&!new URL(r.url()).hostname.match(/^(127\.0\.0\.1|localhost)$/))outside.push(new URL(r.url()).origin)});
 await page.goto("/reading/cambridge-18/cambridge-18-test-01");
 const post=page.waitForResponse(r=>r.request().method()==="POST"&&r.url().endsWith("/api/alua/reading/attempts"));
 await page.getByRole("button",{name:"Start test",exact:true}).click();const created=await(await post).json();expect(created.status).toBe("in_progress");
 await expect(page.getByRole("button",{name:"Finish",exact:true})).toBeVisible();
 const asset=page.locator(".reading-asset img").first();await expect(asset).toBeVisible();await expect.poll(()=>asset.evaluate((el:HTMLImageElement)=>el.naturalWidth)).toBeGreaterThan(0);
 console.log(`Local ${test.info().project.name}: exam ready + authenticated PNG in ${Date.now()-started} ms`);
 if(process.env.ALUA_C_SCREENSHOTS)await page.screenshot({path:`${process.env.ALUA_C_SCREENSHOTS}/release-${test.info().project.name}-exam.png`});
 await page.getByLabel("Answer 1",{exact:true}).fill("lettuce");await page.getByLabel("Answer 2",{exact:true}).fill("tomato");await expect(page.getByText("All changes saved",{exact:true})).toBeVisible();
 await page.reload();await expect(page.getByLabel("Answer 1",{exact:true})).toHaveValue("lettuce");await expect(page).toHaveURL(new RegExp(`/reading/attempts/${created.id}$`));
 await page.getByRole("button",{name:"Passage 3",exact:true}).click();await page.getByRole("button",{name:"Passage 1",exact:true}).click();await expect(page.getByLabel("Answer 2",{exact:true})).toHaveValue("tomato");
 await page.getByRole("button",{name:"Finish",exact:true}).click();const submitted=page.waitForResponse(r=>r.url().endsWith(`/reading/attempts/${created.id}/submit`));
 await page.getByRole("button",{name:"Finish test",exact:true}).click();const terminal=await(await submitted).json();expect(terminal.status).toBe("submitted");expect(terminal.result.total_questions).toBe(40);
 await expect(page.getByRole("heading",{name:"Your result."})).toBeVisible();await expect(page.getByText(`${terminal.result.raw_score} / 40`,{exact:true})).toHaveText(`${terminal.result.raw_score} / 40`);
 if(process.env.ALUA_C_SCREENSHOTS)await page.screenshot({path:`${process.env.ALUA_C_SCREENSHOTS}/release-${test.info().project.name}-result.png`});
 await page.getByRole("link",{name:/^Review (?:\d+ mistakes?|all answers)$/}).click();await expect(page.getByLabel("Answer 1",{exact:true})).toBeDisabled();await expect(page.getByText("Correct answer:",{exact:false}).first()).toBeVisible();
 await page.getByRole("link",{name:"Result",exact:true}).click();await page.getByRole("link",{name:"Back to Reading",exact:true}).click();await page.getByRole("link",{name:"My attempts",exact:true}).click();await expect(page.getByRole("link",{name:"View result"}).first()).toBeVisible();
 await page.goto(`/reading/attempts/${created.id}/result`);await expect(page.getByRole("heading",{name:"Your result."})).toBeVisible();expect(outside).toEqual([]);
});

for(const count of [15,40])test(`atomic hotfix Reading ${count} rapid answers, 422 recovery, reload and confirmed final snapshot`,async({page})=>{
 await page.goto('/reading/cambridge-18/cambridge-18-test-01');await page.getByRole('button',{name:'Start test',exact:true}).click();await page.getByRole('button',{name:'Finish',exact:true}).waitFor();
 for(let n=1;n<=count;n++){
  if(n===14||n===27)await page.getByRole('button',{name:`Passage ${n===14?2:3}`,exact:true}).click();
  const control=page.getByLabel(`Answer ${n}`,{exact:true});
  if(await control.evaluate(e=>e.tagName==='INPUT'))await control.fill('fixture');else await control.locator('button:not(:disabled)').first().click();
 }
 let rejected=false;const events:{event_id:string}[]=[];
 await page.route('**/api/alua/reading/attempts/*/submit',async route=>{const body=route.request().postDataJSON();events.push(body);if(!rejected){rejected=true;await route.fulfill({status:422,json:{detail:Object.keys(body).filter(k=>!['event_id','expected_version'].includes(k)).map(k=>({loc:['body',k],type:'extra_forbidden'}))}});return;}await route.continue();});
 await page.getByRole('button',{name:'Finish',exact:true}).click();await page.getByRole('button',{name:'Finish test',exact:true}).click();await expect(page.getByRole('button',{name:'Finish',exact:true})).toBeEnabled();await expect(page.getByText(/server rejected this request/)).toBeVisible();
 await page.getByRole('button',{name:'Passage 1',exact:true}).click();await page.getByLabel('Answer 1',{exact:true}).fill('recovered');await expect(page.locator('.save-status')).toHaveText('All changes saved');await page.reload();await expect(page.getByLabel('Answer 1',{exact:true})).toHaveValue('recovered');await expect(page.getByLabel('Answer 1',{exact:true})).toBeEnabled();
 await page.getByRole('button',{name:'Finish',exact:true}).click();const submitted=page.waitForResponse(r=>r.url().endsWith('/submit')&&r.status()===200);await page.getByRole('button',{name:'Finish test',exact:true}).click();const final=await(await submitted).json();expect(final.final_snapshot_accepted).toBe(true);expect(Object.values(final.answers).filter(Boolean)).toHaveLength(count);expect(final.result.positions.filter((p:{user_answer:string})=>p.user_answer)).toHaveLength(count);expect(events[1]!.event_id).not.toBe(events[0]!.event_id);await expect(page.getByRole('heading',{name:'Your result.'})).toBeVisible();
 await page.getByRole('link',{name:/^Review (?:\d+ mistakes?|all answers)$/}).click();await expect(page.getByLabel('Answer 1',{exact:true})).toBeDisabled();
});
