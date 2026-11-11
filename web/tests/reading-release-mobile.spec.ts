import {readingUiCheck} from "./reading-ui-check";
import {test,expect} from "@playwright/test";
import {attemptId,releaseBackend} from "./reading-release-fixture";
// Explicitly start online: host network detection can report offline in emulated Chromium.
test.beforeEach(async({context})=>{await context.setOffline(false)});
test("mobile portrait/landscape draft, Finish, result and readonly review",async({page,context})=>{
 await releaseBackend(context);await page.goto(`/reading/attempts/${attemptId}`);await page.getByRole("button",{name:"Questions",exact:true}).click();
 await page.getByLabel("Answer 1",{exact:true}).fill("lettuce");await page.getByLabel("Answer 2",{exact:true}).fill("tomato");await expect(page.locator(".save-status")).toHaveText("All changes saved");
 await page.setViewportSize({width:844,height:390});await expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await page.setViewportSize({width:390,height:844});await expect(page.getByLabel("Answer 1",{exact:true})).toHaveValue("lettuce");await expect(page.getByRole("button",{name:"Finish",exact:true})).toBeVisible();
 await page.getByRole("button",{name:"Finish",exact:true}).click();await page.getByRole("button",{name:"Finish test",exact:true}).click();await expect(page.getByRole("region",{name:"Test result"})).toBeVisible();
 await page.getByRole("link",{name:/^Review test/}).click();await page.getByRole("button",{name:"Questions",exact:true}).click();await expect(page.getByLabel("Answer 1",{exact:true})).toBeDisabled();
});

test("exam UI: centered Finish, silent autosave, reload and visible save errors",async({page,context},info)=>{await readingUiCheck(page,context,info.project.name)});
