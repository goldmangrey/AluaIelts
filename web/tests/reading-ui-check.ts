import {expect,type BrowserContext,type Page} from "@playwright/test";
import {attemptId,exam,releaseBackend} from "./reading-release-fixture";
import {expectCenteredDialog,expectNoSaveIndicators,watchSaveIndicators} from "./exam-ui-assertions";
export async function readingUiCheck(page:Page,context:BrowserContext,project:string){
 const backend=await releaseBackend(context);await page.goto(`/reading/attempts/${attemptId}`);await expect(page.getByRole("button",{name:"Finish",exact:true})).toBeVisible();
 const questions=page.getByRole("button",{name:"Questions",exact:true});if(await questions.isVisible())await questions.click();
 const input=page.getByLabel("Answer 1",{exact:true});await expect(input).toBeEnabled();await watchSaveIndicators(page);
 const qid=exam.passages[0]!.question_groups[0]!.questions[0]!.id;
 await input.fill("reload check");await expect.poll(()=>backend.server().answers[qid]).toBe("reload check");await expectNoSaveIndicators(page);
 await page.reload();await expect(page.getByRole("button",{name:"Finish",exact:true})).toBeVisible();if(await questions.isVisible())await questions.click();await expect(input).toHaveValue("reload check");await watchSaveIndicators(page);
 backend.fail(true);await input.fill("retry preserved");await expect(page.getByRole("alert").filter({hasText:/save|connection|unavailable|retry/i})).toBeVisible();
 await expectNoSaveIndicators(page);backend.fail(false);await page.getByRole("button",{name:"Retry save",exact:true}).click();
 await expect.poll(()=>backend.server().answers[qid]).toBe("retry preserved");await expectNoSaveIndicators(page);
 await page.locator(".questions-scroll").evaluate(el=>{el.scrollTop=300});await page.locator("main").evaluate(el=>{el.style.transform="translateZ(0)"});
 await page.getByRole("button",{name:"Finish",exact:true}).click();const dialog=page.getByRole("dialog",{name:"Finish your test?"});await expectCenteredDialog(page,dialog);
 await page.screenshot({path:`.next/exam-ui-reading-${project}.png`});
 await page.getByRole("button",{name:"Return to test",exact:true}).click();await expect(dialog).toBeHidden();
 await page.getByRole("button",{name:"Finish",exact:true}).click();await page.keyboard.press("Escape");await expect(dialog).toBeHidden();
 if(page.viewportSize()!.width<760){await page.setViewportSize({width:390,height:320});await page.getByRole("button",{name:"Finish",exact:true}).click();await expectCenteredDialog(page,dialog);await expect(dialog.getByRole("button",{name:"Finish test",exact:true})).toBeInViewport();await page.keyboard.press("Escape");}
 expect(backend.events.filter(e=>e.path.endsWith("/submit"))).toHaveLength(0);
}
