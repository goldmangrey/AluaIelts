import {test,expect} from "@playwright/test";
import {attemptId,exam,releaseBackend} from "./reading-release-fixture";
const path=`/reading/attempts/${attemptId}`;
test("home → catalog → explicit Start → durable answers → Finish → real backend result fixture → readonly review → history",async({page,context})=>{
 const backend=await releaseBackend(context,{existing:false});
 await page.goto("/");await page.getByRole("link",{name:/Reading/}).click();await page.getByRole("link",{name:"Cambridge 18"}).click();await page.getByRole("link",{name:/Test 1/}).click();
 await page.getByRole("button",{name:"Start test",exact:true}).dblclick();await expect(page.getByRole("button",{name:"Finish",exact:true})).toBeVisible();
 expect(backend.events.filter(e=>e.path==="/reading/attempts")).toHaveLength(1);
 await page.getByLabel("Answer 1",{exact:true}).fill("lettuce");await page.getByLabel("Answer 2",{exact:true}).fill("tomato");await expect(page.getByText("All answers saved",{exact:true})).toBeVisible();
 await page.getByRole("button",{name:"Mark question 1 for review",exact:true}).click();await page.getByRole("button",{name:"Increase passage text size"}).click();
 await page.getByRole("button",{name:"Passage 2",exact:true}).click();await page.getByRole("button",{name:"Passage 1",exact:true}).click();
 await page.reload();await expect(page.getByLabel("Answer 1",{exact:true})).toHaveValue("lettuce");await expect(page.getByRole("button",{name:"Unmark question 1 for review",exact:true})).toBeVisible();
 await page.getByRole("button",{name:"Finish",exact:true}).click();await expect(page.getByRole("dialog",{name:"Finish test?"})).toContainText("2 of 40");await page.getByRole("button",{name:"Return to test"}).click();expect(backend.events.filter(e=>e.path.endsWith("/submit"))).toHaveLength(0);
 await page.getByRole("button",{name:"Finish",exact:true}).click();await page.getByRole("button",{name:"Finish test",exact:true}).click();
 await expect(page).toHaveURL(`${page.url().split("/reading")[0]}${path}/result`);await expect(page.getByRole("heading",{name:"Completed."})).toBeVisible();
 await page.getByRole("link",{name:"Review answers",exact:true}).click();await expect(page.getByLabel("Answer 1",{exact:true})).toBeDisabled();await expect(page.getByText("Review · Read only",{exact:true})).toBeVisible();
 await page.getByRole("link",{name:"Result",exact:true}).click();await page.getByRole("link",{name:"My attempts",exact:true}).click();await expect(page.getByRole("heading",{name:"My attempts."})).toBeVisible();await expect(page.getByRole("link",{name:"View result"})).toBeVisible();
 expect(backend.events.filter(e=>e.path.endsWith("/submit"))).toHaveLength(1);
});

test("device drafts survive server outage, refresh, close/reopen; offline typing recovers",async({page,context})=>{
 const backend=await releaseBackend(context);backend.fail(true);
 await page.goto(path);await page.getByLabel("Answer 1",{exact:true}).fill("local unsynced");await expect(page.getByText("Save failed · Retry",{exact:true})).toBeVisible();
 page.on("dialog",dialog=>dialog.accept());await page.reload();await expect(page.getByLabel("Answer 1",{exact:true})).toHaveValue("local unsynced");
 await page.close();const reopened=await context.newPage();await reopened.goto(path);await expect(reopened.getByLabel("Answer 1",{exact:true})).toHaveValue("local unsynced");
 backend.fail(false);await context.setOffline(true);await reopened.getByLabel("Answer 1",{exact:true}).fill("offline draft");await expect(reopened.getByText("Offline · Saved on this device",{exact:true})).toBeVisible();
 await context.setOffline(false);await expect(reopened.getByText("All answers saved",{exact:true})).toBeVisible();expect(Object.values(backend.server().answers)).toContain("offline draft");
});

test("two tabs are fenced; remote conflicts preserve both choices; another UID cannot see drafts/results",async({page,context})=>{
 const backend=await releaseBackend(context);await page.goto(path);await expect(page.getByRole("button",{name:"Finish",exact:true})).toBeVisible();
 const second=await context.newPage();await second.goto(path);await expect(second.getByText("Open in another tab · Read only",{exact:true})).toBeVisible();await expect(second.getByLabel("Answer 1",{exact:true})).toBeDisabled();await second.close();
 const q=exam.passages[0]!.question_groups[0]!.questions[0]!;
 await page.getByLabel("Answer 1",{exact:true}).fill("mine");backend.remote({[q.id]:"theirs"});
 await expect(page.getByRole("dialog",{name:"Choose which answers to keep"})).toBeVisible();await expect(page.getByText("This device: mine")).toBeVisible();await expect(page.getByText("Server: theirs")).toBeVisible();
 await page.getByRole("radio",{name:"This device: mine"}).check();await page.getByRole("button",{name:"Save chosen answers"}).click();await expect(page.getByText("All answers saved",{exact:true})).toBeVisible();
 await page.evaluate(()=>localStorage.setItem("release-uid","fixture-B"));await page.reload();await expect(page.getByText(/may not belong to this account/)).toBeVisible();await expect(page.getByLabel("Answer 1",{exact:true})).toHaveCount(0);
});

test("unknown sync replays UUID; unknown Finish recovers terminal result without a second grading",async({page,context})=>{
 const backend=await releaseBackend(context);backend.unknownSave(true);await page.goto(path);await page.getByLabel("Answer 1",{exact:true}).fill("lettuce");await page.getByLabel("Answer 2",{exact:true}).fill("tomato");
 await expect(page.getByText("All answers saved",{exact:true})).toBeVisible();const saves=backend.events.filter(e=>e.path.endsWith("/sync"));expect(saves.length).toBeGreaterThan(1);expect(saves[0]!.body).toEqual(saves[1]!.body);
 backend.unknownSubmit(true);await page.getByRole("button",{name:"Finish",exact:true}).click();await page.getByRole("button",{name:"Finish test",exact:true}).click();await expect(page.getByText("Submission unknown — retry safely")).toBeVisible();
 page.on("dialog",d=>d.accept());await page.reload();await page.getByRole("link",{name:"View result"}).click();await expect(page.getByRole("heading",{name:"Completed."})).toBeVisible();
 const submits=backend.events.filter(e=>e.path.endsWith("/submit"));expect(new Set(submits.map(e=>e.body.event_id)).size).toBe(1);
});

test("server expiry rejects late local edits and direct result/review is terminal readonly",async({page,context})=>{
 const backend=await releaseBackend(context);await page.goto(path);await expect(page.getByLabel("Answer 1",{exact:true})).toBeEnabled();backend.expire();await page.getByLabel("Answer 1",{exact:true}).fill("too late");
 await expect(page).toHaveURL(new RegExp(`${path}/result$`));await expect(page.getByRole("heading",{name:"Time elapsed."})).toBeVisible();await expect(page.getByText(/local answers differ from the server result/)).toBeVisible();
 await page.getByRole("link",{name:"Review answers"}).click();await expect(page.getByLabel("Answer 1",{exact:true})).toBeDisabled();expect(backend.events.some(e=>e.path.endsWith("/submit"))).toBe(false);
});

test("stable text highlights and view preferences survive resizing, passages and refresh",async({page,context})=>{
 await releaseBackend(context);await page.goto(path);const block=page.locator("[data-highlight-block]").first();await expect(block).toBeVisible();
 const quote=await block.evaluate(el=>{const node=el.firstChild!;const range=document.createRange();range.setStart(node,0);range.setEnd(node,Math.min(35,node.textContent!.length));const selection=window.getSelection()!;selection.removeAllRanges();selection.addRange(range);el.dispatchEvent(new MouseEvent("mouseup",{bubbles:true}));return range.toString()});
 await page.getByRole("button",{name:"Highlight",exact:true}).click();await expect(page.locator("mark")).toHaveText(quote);
 await page.getByRole("button",{name:"Increase passage text size"}).click();await page.getByRole("separator").press("ArrowRight");await page.getByRole("button",{name:"Passage 2",exact:true}).click();await page.getByRole("button",{name:"Passage 1",exact:true}).click();
 await expect(page.getByText("Saving on this device…",{exact:true})).toHaveCount(0);await page.reload();await expect(page.locator("mark")).toHaveText(quote);await expect(page.getByRole("separator")).toHaveAttribute("aria-valuenow","52");
 await page.getByRole("button",{name:"Clear passage highlights"}).click();await expect(page.locator("mark")).toHaveCount(0);
});

test("deadline reached offline pauses editing, reconnect confirms server expiry and preserves unsent draft",async({page,context})=>{
 await page.clock.install();const backend=await releaseBackend(context,{seconds:10});await page.goto(path);await expect(page.getByLabel("Answer 1",{exact:true})).toBeEnabled();
 await context.setOffline(true);await page.getByLabel("Answer 1",{exact:true}).fill("offline late draft");await expect(page.getByText("Offline · Saved on this device",{exact:true})).toBeVisible();
 backend.expire();await page.clock.fastForward(11000);await expect(page.getByLabel("Answer 1",{exact:true})).toBeDisabled();await expect(page).toHaveURL(new RegExp(`${path}$`));
 await context.setOffline(false);await expect(page.getByRole("heading",{name:"Time elapsed."})).toBeVisible();await expect(page.getByText(/local answers differ from the server result/)).toBeVisible();expect(backend.server().answers).toEqual({});
});

test("logout cleanup removes the owner's actual IndexedDB drafts and leases",async({page,context})=>{
 await releaseBackend(context);await page.goto(path);await page.getByLabel("Answer 1",{exact:true}).fill("saved draft");await expect(page.getByText("All answers saved",{exact:true})).toBeVisible();
 const count=()=>page.evaluate(()=>new Promise<number>((resolve,reject)=>{const request=indexedDB.open("alua-reading-drafts",1);request.onsuccess=()=>{const tx=request.result.transaction("drafts");const all=tx.objectStore("drafts").getAll();all.onsuccess=()=>resolve(all.result.filter(v=>v.uid==="fixture-A").length);all.onerror=()=>reject(all.error)}}));
 expect(await count()).toBe(1);await page.goto("/profile");await page.getByRole("button",{name:"Log out",exact:true}).click();await expect(page).toHaveURL("http://127.0.0.1:3300/");expect(await count()).toBe(0);
});
