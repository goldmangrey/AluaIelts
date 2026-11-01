import {test,expect} from "@playwright/test";
import {attemptId,releaseBackend} from "./reading-release-fixture";
test("mobile portrait/landscape draft, Finish, result and readonly review",async({page,context})=>{
 await releaseBackend(context);await page.goto(`/reading/attempts/${attemptId}`);await page.getByRole("button",{name:"Questions",exact:true}).click();
 await page.getByLabel("Answer 1",{exact:true}).fill("lettuce");await page.getByLabel("Answer 2",{exact:true}).fill("tomato");await expect(page.getByText("All answers saved",{exact:true})).toBeVisible();
 await page.setViewportSize({width:844,height:390});await expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await page.setViewportSize({width:390,height:844});await expect(page.getByLabel("Answer 1",{exact:true})).toHaveValue("lettuce");await expect(page.getByRole("button",{name:"Finish",exact:true})).toBeVisible();
 await page.getByRole("button",{name:"Finish",exact:true}).click();await page.getByRole("button",{name:"Finish test",exact:true}).click();await expect(page.getByRole("heading",{name:"Completed."})).toBeVisible();
 await page.getByRole("link",{name:"Review answers"}).click();await page.getByRole("button",{name:"Questions",exact:true}).click();await expect(page.getByLabel("Answer 1",{exact:true})).toBeDisabled();
});
