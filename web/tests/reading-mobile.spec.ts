import {test,expect} from "@playwright/test";
import {openExam} from "./reading-fixture";
test("mobile toggles retain answers, passage and independent scroll",async({page})=>{
  await openExam(page);
  const left=page.locator(".passage-scroll"),right=page.locator(".questions-scroll");
  await expect(left).toBeVisible();await expect(right).toBeHidden();
  await left.evaluate(e=>e.scrollTop=120);
  await page.getByRole("button",{name:"Questions",exact:true}).click();
  await expect(right).toBeVisible();await expect(left).toBeHidden();
  await page.getByLabel("Answer 1",{exact:true}).fill("mobile answer");
  await page.getByRole("button",{name:"Passage",exact:true}).click();
  expect(await left.evaluate(e=>e.scrollTop)).toBe(120);
  await page.getByRole("button",{name:"Questions",exact:true}).click();
  await expect(page.getByLabel("Answer 1",{exact:true})).toHaveValue("mobile answer");
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await expect(page.getByText("All answers saved",{exact:true})).toBeVisible();
});
