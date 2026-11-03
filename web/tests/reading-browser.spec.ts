import { join } from "node:path";
import { test, expect } from "@playwright/test";
import { fixtures, openExam } from "./reading-fixture";
import { allQuestions } from "../src/features/reading/exam/models";

test("desktop columns, independent scroll, stable input, passage restore and question navigation",async({page},info)=>{
  const errors:string[]=[];page.on("pageerror",e=>errors.push(e.message));
  await openExam(page);
  const text=page.locator(".passage-scroll"),questions=page.locator(".questions-scroll");
  await expect(text).toBeVisible();await expect(questions).toBeVisible();
  await page.screenshot({path:process.env.ALUA_C_SCREENSHOTS ? join(process.env.ALUA_C_SCREENSHOTS, `exam-${info.project.name}.png`) : info.outputPath("exam-desktop.png")});
  const l=await text.boundingBox(),r=await questions.boundingBox();expect(r!.x).toBeGreaterThan(l!.x+l!.width-2);
  await text.evaluate(e=>e.scrollTop=220);
  await questions.evaluate(e=>e.scrollTop=170);
  expect(await text.evaluate(e=>e.scrollTop)).toBe(220);
  await questions.evaluate(e=>e.scrollTop=0);
  const answer=page.getByLabel("Answer 1",{exact:true});await expect(answer).toHaveValue("restored draft");
  await answer.focus();await answer.evaluate(e=>e.setAttribute("data-qa-stable","yes"));
  await answer.fill("my answer");await answer.pressSequentially(" text");
  await expect(answer).toBeFocused();await expect(answer).toHaveAttribute("data-qa-stable","yes");
  expect(await text.evaluate(e=>e.scrollTop)).toBe(220);
  await expect(page.getByText("All answers saved",{exact:true})).toBeVisible();
  await questions.evaluate(e=>e.scrollTop=180);
  await page.getByRole("button",{name:"Passage 2",exact:true}).click();
  await page.getByRole("button",{name:"Passage 1",exact:true}).click();
  expect(await text.evaluate(e=>e.scrollTop)).toBe(220);expect(await questions.evaluate(e=>e.scrollTop)).toBe(180);
  await expect(answer).toHaveValue("my answer text");
  await page.getByRole("button",{name:"Question 12, unanswered",exact:true}).click();
  expect(await text.evaluate(e=>e.scrollTop)).toBe(220);
  await page.getByRole("button",{name:"All 40",exact:true}).click();
  await page.getByRole("dialog").getByRole("button",{name:"Question 30, unanswered",exact:true}).click();
  await expect(page.getByRole("button",{name:"Passage 3",exact:true})).toHaveAttribute("aria-current","true");
  await expect(page.getByRole("button",{name:"All 40",exact:true})).toBeFocused();
  await page.getByRole("button",{name:"All 40",exact:true}).click();await page.keyboard.press("Escape");
  await expect(page.getByRole("button",{name:"All 40",exact:true})).toBeFocused();
  const separator=page.getByRole("separator");await separator.focus();await page.keyboard.press("ArrowRight");await expect(separator).toHaveAttribute("aria-valuenow","52");
  const handle=await separator.boundingBox();await page.mouse.move(handle!.x+2,handle!.y+50);await page.mouse.down();
  await page.mouse.move((page.viewportSize()!.width)*.9,handle!.y+50);await page.mouse.up();
  await expect(separator).toHaveAttribute("aria-valuenow","60");
  await page.getByRole("button",{name:"Increase passage text size"}).click();
  await expect(page.locator(".passage-article")).toHaveCSS("font-size","17px");
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);expect(errors).toEqual([]);
});

test("real question families, checkbox positions, images, marks and no client exceptions",async({page})=>{
  const errors:string[]=[];page.on("pageerror",e=>errors.push(e.message));
  const ids=[...new Set(Object.values(fixtures.samples))];const seen=new Set<string>();
  for(const id of ids){
    const {exam}=await openExam(page,id);
    for(const p of exam.passages){
      await page.getByRole("button",{name:`Passage ${p.number}`,exact:true}).click();
      for(const group of p.question_groups){
        seen.add(group.type);
        const scope=page.locator(`[data-question-type="${group.type}"]`).filter({visible:true}).first();
        await expect(scope).toBeVisible();
        const radios=scope.getByRole("radio");if(await radios.count()){await radios.first().check();await expect(radios.first()).toBeChecked();}
        const selects=scope.getByRole("combobox");if(await selects.count()){await selects.first().selectOption({index:1});await expect(selects.first()).not.toHaveValue("");}
        const inputs=scope.getByRole("textbox");if(await inputs.count()){await inputs.first().fill("practice");await expect(inputs.first()).toHaveValue("practice");}
        if(group.type==="multiple_choice_multiple" && group.options.length && group.id===p.question_groups.find(g=>g.type==="multiple_choice_multiple")?.id){
          const boxes=scope.getByRole("checkbox");if(await boxes.count()>1){await boxes.nth(0).check();await boxes.nth(1).check();await expect(boxes.nth(0)).toBeChecked();await expect(boxes.nth(1)).toBeChecked();}
        }
      }
      const assets=page.locator(".questions-scroll > section:not([hidden]) .reading-asset");
      for(let i=0;i<await assets.count();i++) {
        const img=assets.nth(i).locator("img");await expect(img).toBeVisible();
        await expect.poll(()=>img.evaluate(e=>(e as HTMLImageElement).naturalWidth)).toBeGreaterThan(0);
      }
    }
    // No Finish or automatic submission is part of Phase C.
    expect(await page.getByRole("button",{name:/finish|submit/i}).count()).toBe(0);
    await expect(page.getByText("All answers saved",{exact:true})).toBeVisible();
    await page.reload(); // No start endpoint; same fixture attempt remains.
    await expect(page.getByRole("button",{name:"All 40",exact:true})).toBeVisible();
  }
  expect(seen.size).toBe(15);expect(errors).toEqual([]);
});

test("save failure keeps answers and explicit retry; review and source image failure are visible",async({page})=>{
  const {exam}=await openExam(page);
  await page.route("**/reading-qa/save",route=>route.fulfill({status:503}));
  const answer=page.getByLabel("Answer 1",{exact:true});await answer.fill("unsaved draft");
  await expect(page.getByText("Not saved",{exact:true})).toBeVisible();await expect(answer).toHaveValue("unsaved draft");
  await page.getByRole("button",{name:"Mark question 1 for review",exact:true}).click();
  await expect(page.getByRole("button",{name:"Question 1, answered, marked for review",exact:true})).toBeVisible();
  await expect(page.getByRole("button",{name:"Retry save",exact:true})).toBeVisible();
  expect(allQuestions(exam)).toHaveLength(40);
  // The image is real content when available; this route simulates its absence explicitly.
  await page.unroute("**/reading-qa/save");
  await page.route("**/reading-qa/asset/**",route=>route.fulfill({status:404}));
  await page.goto("/reading-qa/cambridge-04-test-01");
  await page.getByRole("button",{name:"Passage 2",exact:true}).click();
  await expect(page.getByText("Task image couldn’t load.",{exact:false}).first()).toBeVisible();
  await expect(page.getByRole("button",{name:"Retry image"}).first()).toBeVisible();
});

test("quick question UX: real answer values, toggle, inline summary and Question 14 deduplication",async({page},info)=>{
 const {events}=await openExam(page);
 const tf=page.locator('[data-question-type="true_false_not_given"] [data-question="8"]');
 const truth=tf.getByRole('button',{name:'TRUE',exact:true});
 await truth.click();await expect(truth).toHaveAttribute('aria-pressed','true');
 await expect(page.getByText('All answers saved',{exact:true})).toBeVisible();
 await expect.poll(()=>events.some(e=>e.answers['cambridge-18-test-01-q-08']==='TRUE')).toBe(true);
 await truth.click();await expect(truth).toHaveAttribute('aria-pressed','false');
 await expect(page.getByText('All answers saved',{exact:true})).toBeVisible();
 await expect.poll(()=>events.some(e=>e.answers['cambridge-18-test-01-q-08']==='')).toBe(true);
 await page.getByRole('button',{name:'Passage 2',exact:true}).click();
 const matching=page.getByRole('group',{name:'Answer 14',exact:true});
 await matching.getByRole('button',{name:'A',exact:true}).click();
 await expect(page.getByText('All answers saved',{exact:true})).toBeVisible();
 await expect.poll(()=>events.some(e=>e.answers['cambridge-18-test-01-q-14']==='A')).toBe(true);
 await page.getByRole('button',{name:'Passage 1',exact:true}).click();await page.getByRole('button',{name:'Passage 2',exact:true}).click();
 await expect(matching.getByRole('button',{name:'A',exact:true})).toHaveAttribute('aria-pressed','true');
 await page.getByRole('button',{name:'Passage 3',exact:true}).click();
 const summary=page.locator('[data-question-type="summary_completion"]');
 const input=summary.getByLabel('Answer 32',{exact:true});await input.fill('orbit');
 await expect(input).toHaveCSS('width','160px');await expect(input).toHaveCSS('height','40px');
 await expect(summary.locator('.word-limit')).toHaveCount(0);
 await summary.getByRole('button',{name:'Mark question 32 for review',exact:true}).click();
 await expect(summary.getByRole('button',{name:'Unmark question 32 for review',exact:true})).toHaveAttribute('aria-pressed','true');
 await expect(page.getByText('All answers saved',{exact:true})).toBeVisible();
 await expect.poll(()=>events.some(e=>e.answers['cambridge-18-test-01-q-32']==='orbit')).toBe(true);
 await summary.scrollIntoViewIfNeeded();await page.screenshot({path:info.outputPath('summary-desktop.png')});
 await page.setViewportSize({width:390,height:844});await page.getByRole('button',{name:'Questions',exact:true}).click();await summary.scrollIntoViewIfNeeded();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await page.screenshot({path:info.outputPath('summary-mobile.png'),scale:'css'});
 await page.setViewportSize({width:1440,height:900});
 await openExam(page,'cambridge-04-test-01');
 const radioGroup=page.locator('[data-question="14"]');
 await expect(radioGroup.getByRole('radio')).toHaveCount(5);
 const contents=(await radioGroup.innerText()).replace(/\s+/g,' ');
 expect(contents.split('Which of the following is the most suitable title for Reading Passage 1?')).toHaveLength(2);
 expect(contents.split('The importance of the rainforests and the reasons for their destruction')).toHaveLength(2);
 const radio=radioGroup.getByRole('radio').first();await radio.check();await expect(radio).toBeChecked();await radio.click();await expect(radio).not.toBeChecked();
 await radioGroup.scrollIntoViewIfNeeded();await page.screenshot({path:info.outputPath('question-14.png')});
 await page.getByRole('button',{name:'Passage 3',exact:true}).click();
 const letters=page.getByRole('group',{name:'Answer 30',exact:true});
 await expect(letters.getByRole('button')).toHaveText(['A','B','C','D','E']);
 await letters.getByRole('button',{name:'E',exact:true}).click();await expect(letters.getByRole('button',{name:'E',exact:true})).toHaveAttribute('aria-pressed','true');
 await expect(page.locator('select')).toHaveCount(0);
});
