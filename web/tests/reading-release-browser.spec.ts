import {test,expect} from "@playwright/test";
import {attemptId,data,exam,releaseBackend} from "./reading-release-fixture";
import type { Attempt } from "../src/features/reading/exam/models";
import type { ReadingResult } from "../src/features/reading/exam/results";
const path=`/reading/attempts/${attemptId}`;
test("home → catalog → explicit Start → durable answers → Finish → real backend result fixture → readonly review → history",async({page,context})=>{
 const backend=await releaseBackend(context,{existing:false});
 await page.goto("/");await page.getByRole("link",{name:/Reading/}).click();await page.getByRole("link",{name:"18 Cambridge IELTS"}).click();await page.getByRole("link",{name:/Test 1/}).click();
 await page.getByRole("button",{name:"Start test",exact:true}).dblclick();await expect(page.getByRole("button",{name:"Finish",exact:true})).toBeVisible();
 expect(backend.events.filter(e=>e.path==="/reading/attempts")).toHaveLength(1);
 await page.getByLabel("Answer 1",{exact:true}).fill("lettuce");await page.getByLabel("Answer 2",{exact:true}).fill("tomato");await expect(page.locator(".save-status")).toHaveText("");
 await page.getByRole("button",{name:"Mark question 1 for review",exact:true}).click();await page.getByRole("button",{name:"20px · Large"}).click();
 await page.getByRole("button",{name:"Passage 2",exact:true}).click();await page.getByRole("button",{name:"Passage 1",exact:true}).click();
 await page.reload();await expect(page.getByLabel("Answer 1",{exact:true})).toHaveValue("lettuce");await expect(page.getByRole("button",{name:"Unmark question 1 for review",exact:true})).toBeVisible();
 await page.getByRole("button",{name:"Finish",exact:true}).click();await expect(page.getByRole("dialog",{name:"Finish your test?"})).toContainText("2 of 40");await page.getByRole("button",{name:"Return to test"}).click();expect(backend.events.filter(e=>e.path.endsWith("/submit"))).toHaveLength(0);
 await page.getByRole("button",{name:"Finish",exact:true}).click();await page.getByRole("button",{name:"Finish test",exact:true}).click();
 await expect(page).toHaveURL(`${page.url().split("/reading")[0]}${path}/result`);await expect(page.getByRole("heading",{name:"Your result."})).toBeVisible();
 await page.getByRole("link",{name:/^Review (?:\d+ mistakes?|all answers)$/}).click();await expect(page.getByLabel("Answer 1",{exact:true})).toBeDisabled();await expect(page.getByText("Review · Read only",{exact:true})).toBeVisible();
 await page.getByRole("link",{name:"Result",exact:true}).click();await page.getByRole("link",{name:"Back to Reading",exact:true}).click();await page.getByRole("link",{name:"My attempts",exact:true}).click();await expect(page.getByRole("heading",{name:"My attempts."})).toBeVisible();await expect(page.getByRole("link",{name:"View result"})).toBeVisible();
 expect(backend.events.filter(e=>e.path.endsWith("/submit"))).toHaveLength(1);
});

test("device drafts survive server outage, refresh, close/reopen; offline typing recovers",async({page,context})=>{
 const backend=await releaseBackend(context);backend.fail(true);
 await page.goto(path);await page.getByLabel("Answer 1",{exact:true}).fill("local unsynced");await expect(page.getByText("Save failed · Retry",{exact:true})).toBeVisible();
 page.on("dialog",dialog=>dialog.accept());await page.reload();await expect(page.getByLabel("Answer 1",{exact:true})).toHaveValue("local unsynced");
 await page.close();const reopened=await context.newPage();await reopened.goto(path);await expect(reopened.getByLabel("Answer 1",{exact:true})).toHaveValue("local unsynced");
 backend.fail(false);await context.setOffline(true);await reopened.getByLabel("Answer 1",{exact:true}).fill("offline draft");await expect(reopened.getByText("Offline · Saved on this device",{exact:true})).toBeVisible();
 await context.setOffline(false);await expect(reopened.locator(".save-status")).toHaveText("");expect(Object.values(backend.server().answers)).toContain("offline draft");
});

test("two tabs are fenced; remote conflicts preserve both choices; another UID cannot see drafts/results",async({page,context})=>{
 const backend=await releaseBackend(context);await page.goto(path);await expect(page.getByRole("button",{name:"Finish",exact:true})).toBeVisible();
 const second=await context.newPage();await second.goto(path);await expect(second.getByText("Open in another tab · Read only",{exact:true})).toBeVisible();await expect(second.getByLabel("Answer 1",{exact:true})).toBeDisabled();await second.close();
 const q=exam.passages[0]!.question_groups[0]!.questions[0]!;
 await page.getByLabel("Answer 1",{exact:true}).fill("mine");backend.remote({[q.id]:"theirs"});
 await expect(page.getByRole("dialog",{name:"Choose which answers to keep"})).toBeVisible();await expect(page.getByText("This device: mine")).toBeVisible();await expect(page.getByText("Server: theirs")).toBeVisible();
 await page.getByRole("radio",{name:"This device: mine"}).check();await page.getByRole("button",{name:"Save chosen answers"}).click();await expect(page.locator(".save-status")).toHaveText("");
 await page.evaluate(()=>localStorage.setItem("release-uid","fixture-B"));await page.reload();await expect(page.getByText(/may not belong to this account/)).toBeVisible();await expect(page.getByLabel("Answer 1",{exact:true})).toHaveCount(0);
});

test("unknown sync replays UUID; unknown Finish recovers terminal result without a second grading",async({page,context})=>{
 const backend=await releaseBackend(context);backend.unknownSave(true);await page.goto(path);await page.getByLabel("Answer 1",{exact:true}).fill("lettuce");await page.getByLabel("Answer 2",{exact:true}).fill("tomato");
 await expect(page.locator(".save-status")).toHaveText("");const saves=backend.events.filter(e=>e.path.endsWith("/sync"));expect(saves.length).toBeGreaterThan(1);expect(saves[0]!.body).toEqual(saves[1]!.body);
 backend.unknownSubmit(true);await page.getByRole("button",{name:"Finish",exact:true}).click();await page.getByRole("button",{name:"Finish test",exact:true}).click();await expect(page.getByText("Submission unknown — retry safely")).toBeVisible();
 page.on("dialog",d=>d.accept());await page.reload();await page.getByRole("link",{name:"View result"}).click();await expect(page.getByRole("heading",{name:"Your result."})).toBeVisible();
 const submits=backend.events.filter(e=>e.path.endsWith("/submit"));expect(new Set(submits.map(e=>e.body.event_id)).size).toBe(1);
});

test("server expiry rejects late local edits and direct result/review is terminal readonly",async({page,context})=>{
 const backend=await releaseBackend(context);await page.goto(path);await expect(page.getByLabel("Answer 1",{exact:true})).toBeEnabled();backend.expire();await page.getByLabel("Answer 1",{exact:true}).fill("too late");
 await expect(page).toHaveURL(new RegExp(`${path}/result$`));await expect(page.getByText("Time expired · Academic Reading",{exact:true})).toBeVisible();await expect(page.getByText(/local answers differ from the server result/)).toBeVisible();
 await page.getByRole("link",{name:/^Review (?:\d+ mistakes?|all answers)$/}).click();await expect(page.getByLabel("Answer 1",{exact:true})).toBeDisabled();expect(backend.events.some(e=>e.path.endsWith("/submit"))).toBe(false);
});

test("stable text highlights and view preferences survive resizing, passages and refresh",async({page,context})=>{
 await releaseBackend(context);await page.goto(path);const block=page.locator("[data-highlight-block]").first();await expect(block).toBeVisible();
 const quote=await block.evaluate(el=>{const node=el.firstChild!;const range=document.createRange();range.setStart(node,0);range.setEnd(node,Math.min(35,node.textContent!.length));const selection=window.getSelection()!;selection.removeAllRanges();selection.addRange(range);el.dispatchEvent(new MouseEvent("mouseup",{bubbles:true}));return range.toString()});
 await page.getByRole("button",{name:"Highlight",exact:true}).click();await expect(page.locator("mark")).toHaveText(quote);
 await page.getByRole("button",{name:"20px · Large"}).click();await page.getByRole("separator").press("ArrowRight");await page.getByRole("button",{name:"Passage 2",exact:true}).click();await page.getByRole("button",{name:"Passage 1",exact:true}).click();
 await expect(page.getByText("Saving on this device…",{exact:true})).toHaveCount(0);await page.reload();await expect(page.locator("mark")).toHaveText(quote);await expect(page.getByRole("separator")).toHaveAttribute("aria-valuenow","52");
 await page.getByRole("button",{name:"Clear passage highlights"}).click();await expect(page.locator("mark")).toHaveCount(0);
});

test("deadline reached offline pauses editing, reconnect confirms server expiry and preserves unsent draft",async({page,context})=>{
 await page.clock.install();const backend=await releaseBackend(context,{seconds:10});await page.goto(path);await expect(page.getByLabel("Answer 1",{exact:true})).toBeEnabled();
 await context.setOffline(true);await page.getByLabel("Answer 1",{exact:true}).fill("offline late draft");await expect(page.getByText("Offline · Saved on this device",{exact:true})).toBeVisible();
 backend.expire();await page.clock.fastForward(11000);await expect(page.getByLabel("Answer 1",{exact:true})).toBeDisabled();await expect(page).toHaveURL(new RegExp(`${path}$`));
 await context.setOffline(false);await expect(page.getByText("Time expired · Academic Reading",{exact:true})).toBeVisible();await expect(page.getByText(/local answers differ from the server result/)).toBeVisible();expect(backend.server().answers).toEqual({});
});

test("logout cleanup removes the owner's actual IndexedDB drafts and leases",async({page,context})=>{
 await releaseBackend(context);await page.goto(path);await page.getByLabel("Answer 1",{exact:true}).fill("saved draft");await expect(page.locator(".save-status")).toHaveText("");
 const count=()=>page.evaluate(()=>new Promise<number>((resolve,reject)=>{const request=indexedDB.open("alua-reading-drafts",1);request.onsuccess=()=>{const tx=request.result.transaction("drafts");const all=tx.objectStore("drafts").getAll();all.onsuccess=()=>resolve(all.result.filter(v=>v.uid==="fixture-A").length);all.onerror=()=>reject(all.error)}}));
 expect(await count()).toBe(1);await page.goto("/profile");await page.getByRole("button",{name:"Log out",exact:true}).click();await expect(page).toHaveURL("http://127.0.0.1:3300/");expect(await count()).toBe(0);
});


test("Reading library: API availability, responsive index, keyboard, hover and navigation", async ({page, context}, info) => {
 await releaseBackend(context);
 // Build this visual fixture from the validated local backend content, never a fixed book range.
 const books = [...new Set(data.exams.map(exam => Number(exam.id.split("-")[1])))].sort((a,b)=>a-b);
 const items = books.map(book_number => ({book_number, exams: data.exams.filter(exam => Number(exam.id.split("-")[1]) === book_number).map((exam, i) => ({exam_id:exam.id, source_book:book_number, source_test_number:Number(exam.id.split("-")[3]), test_ordinal:i+1, enabled_for_private_practice:true, content_status:"needs_review", not_fully_proofread:true, question_count:40, passage_count:3, in_progress_attempt_ids:[]}))}));
 await page.route("**/api/alua/reading/books", route => route.fulfill({json:{dataset_version:"1",items}}));
 await page.setViewportSize({width:1440,height:900});
 await page.goto("/reading");
 const index = page.getByRole("navigation",{name:"Cambridge IELTS collections"});
 const rows = index.getByRole("link");
 await expect(rows).toHaveCount(books.length);
 await expect(page.getByRole("link",{name:"Account"})).toHaveAttribute("href","/profile");
 for (let i=0;i<books.length;i++) await expect(rows.nth(i)).toHaveAttribute("href",`/reading/cambridge-${books[i]}`);
 if (info.project.name === "release-chromium") await page.screenshot({path:"docs/reading-library/desktop.png"});
 for (const width of [320,390,430,768]) {
   await page.setViewportSize({width,height:844});
   expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
   const row = await rows.first().boundingBox();expect(row!.height).toBeGreaterThanOrEqual(68);
   const name = rows.first().locator("span").nth(1);
   expect(await name.evaluate(el=>el.scrollWidth<=el.clientWidth)).toBe(true);
   if(width===390 && info.project.name==="release-chromium") await page.screenshot({path:"docs/reading-library/mobile.png"});
 }
 await page.setViewportSize({width:1440,height:900});
 await rows.first().hover();
 await expect(rows.first().locator("span").first()).toHaveCSS("color","rgb(25, 107, 91)");
 await expect(rows.first().locator("span").last()).toHaveCSS("transform","matrix(1, 0, 0, 1, 3, -3)");
 await page.emulateMedia({reducedMotion:"reduce"});
 await expect(rows.first().locator("span").last()).toHaveCSS("transform","none");
 await expect(rows.first().locator("span").last()).toHaveCSS("transition-duration","0s");
 await page.mouse.move(0,0);
 // WebKit follows macOS full keyboard access: Option+Tab includes links.
 await page.getByRole("link",{name:"My attempts",exact:true}).focus();await page.keyboard.press(info.project.name === "release-webkit" ? "Alt+Tab" : "Tab");
 await expect(rows.first()).toBeFocused();await expect(rows.first()).toHaveCSS("outline-style","solid");
 await page.keyboard.press("Enter");await expect(page).toHaveURL(new RegExp(`/reading/cambridge-${books[0]}$`));
 await expect(page.getByRole("navigation",{name:"Available tests"})).toBeVisible();
 await page.goto("/reading");await page.getByRole("link",{name:"My attempts",exact:true}).click();
 await expect(page.getByRole("heading",{name:"My attempts."})).toBeVisible();
});

test("Reading library: loading, empty, API failure, retry and permissions", async ({page,context}) => {
 await releaseBackend(context);
 let mode="loading";
 let release:()=>void=()=>{};
 const gate=new Promise<void>(resolve=>{release=resolve});
 await page.route("**/api/alua/reading/books",async route=>{
   if(mode==="loading")await gate;
   await route.fulfill(mode==="error"?{status:503,json:{error:{code:"temporary_unavailable"}}}:mode==="forbidden"?{status:403,json:{error:{code:"forbidden"}}}:{json:{dataset_version:"1",items:[]}});
 });
 await page.goto("/reading");await expect(page.getByRole("status")).toHaveText("Loading practice tests…");release();
 await expect(page.getByRole("heading",{name:"No practice tests available."})).toBeVisible();
 mode="error";await page.reload();await expect(page.getByRole("heading",{name:"Practice tests are temporarily unavailable."})).toBeVisible();
 mode="empty";await page.getByRole("button",{name:"Try again"}).click();await expect(page.getByRole("heading",{name:"No practice tests available."})).toBeVisible();
 mode="forbidden";await page.reload();await expect(page.getByRole("heading",{name:"Practice tests aren’t available for this account."})).toBeVisible();
 await page.evaluate(()=>localStorage.setItem("release-signed-out","1"));await page.reload();
 await expect(page.getByRole("heading",{name:"Log in to view practice tests."})).toBeVisible();
 await expect(page.getByRole("banner").getByRole("link",{name:"Log in",exact:true})).toHaveAttribute("href","/login");
 await expect(page.getByRole("main").getByRole("link",{name:"Log in",exact:true})).toHaveAttribute("href","/login?next=%2Freading");
});

test("Result V2: confirmed verdict map, edge scores, responsive layout and exact Review links",async({page,context},info)=>{
 const backend=await releaseBackend(context);
 // UI-only API scenarios clone the existing terminal fixture; no answer key is
 // changed and no attempt is created/submitted. Grading is not tested here.
 const base=structuredClone(data.release_results[0]!.result);
 const attempt:Attempt={...structuredClone(backend.server()),status:"submitted",submitted_at:"2026-11-02T10:30:00Z"};
 let result:ReadingResult={...base,attempt_id:attemptId,estimated_band:7.5,raw_score:32,completion_reason:"submitted" as "submitted"|"deadline",
  positions:base.positions.map((position,i)=>({...position,is_correct:i<32,unanswered:i>=36,user_answer:i>=36?"":"fixture answer"})).reverse()};
 await page.route(`**/api/alua/reading/attempts/${attemptId}`,route=>route.fulfill({json:attempt}));
 await page.route(`**/api/alua/reading/attempts/${attemptId}/result`,route=>route.fulfill({json:result}));
 await page.goto(`${path}/result`);
 const map=page.getByRole("region",{name:"Your 40 answers",exact:true});
 await expect(map.getByRole("link")).toHaveCount(40);
 await expect(map.getByRole("link",{name:/^Question \d+, correct$/})).toHaveCount(32);
 await expect(map.getByRole("link",{name:/^Question \d+, incorrect$/})).toHaveCount(4);
 await expect(map.getByRole("link",{name:/^Question \d+, unanswered$/})).toHaveCount(4);
 await expect(page.getByRole("link",{name:"Review 8 mistakes"})).toBeVisible();
 await expect(page.getByText("7.5",{exact:true})).toBeVisible();
 await expect(map).toHaveCSS("opacity","1");
 for(const [width,height] of [[1440,900],[1280,800],[768,1024],[390,844],[320,844]]){
  await page.setViewportSize({width:width!,height:height!});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  for(const row of exam.passages)await expect(map.getByRole("region",{name:`Passage ${row.number}`,exact:true}).getByRole("link")).toHaveCount(row.question_numbers.length);
  if(info.project.name==="release-chromium"&&(width===1440||width===390))await page.screenshot({path:`docs/result-v2/${width===1440?"desktop":"mobile"}.png`,scale:"css"});
 }
 await page.emulateMedia({reducedMotion:"reduce"});await expect(map).toHaveCSS("animation-name","none");
 const target=base.positions.find(p=>p.number===33)!;
 const cell=map.getByRole("link",{name:`Question 33, ${result.positions.find(p=>p.question_id===target.question_id)!.is_correct?"correct":"incorrect"}`});
 await expect(cell).toHaveAttribute("href",`${path}/review?question=${encodeURIComponent(target.question_id)}`);
 await cell.focus();await page.keyboard.press("Enter");
 await expect(page.getByRole("button",{name:"Passage 3",exact:true})).toHaveAttribute("aria-current","true");
 await expect(page.getByRole("button",{name:/^Question 33,/})).toHaveAttribute("aria-current","true");
 await expect(page.getByLabel("Answer 33",{exact:true})).toBeVisible();await expect(page.getByLabel("Answer 33",{exact:true})).toBeDisabled();
 await page.goto(`${path}/result`);await page.getByRole("link",{name:"Back to Reading",exact:true}).click();await expect(page).toHaveURL(/\/reading$/);
 // Entirely unanswered, no estimate: raw score is primary, no fabricated band.
 result={...result,raw_score:0,estimated_band:null,positions:base.positions.map(p=>({...p,is_correct:false,unanswered:true,user_answer:""}))};
 await page.goto(`${path}/result`);await expect(page.getByRole("link",{name:"Review 40 mistakes"})).toBeVisible();await expect(page.getByText("Estimated IELTS band",{exact:true})).toHaveCount(0);
 await expect(map.getByRole("link",{name:/unanswered$/})).toHaveCount(40);
 result={...result,raw_score:40,estimated_band:9,positions:base.positions.map(p=>({...p,is_correct:true,unanswered:false}))};
 await page.reload();await expect(page.getByRole("link",{name:"Review all answers"})).toBeVisible();await expect(page.getByText("100% correct",{exact:true})).toBeVisible();
 // Move one intact group in the snapshot to exercise nonstandard 7/19/14
 // membership without modifying question IDs, options or answer keys.
 const moved=attempt.exam!.passages[0]!.question_groups.pop()!;
 attempt.exam!.passages[1]!.question_groups.unshift(moved);
 for(const passage of attempt.exam!.passages)passage.question_numbers=passage.question_groups.flatMap(g=>g.questions.map(q=>q.number));
 attempt.status="expired";result={...result,completion_reason:"deadline",positions:result.positions.map(p=>({...p,passage_number:attempt.exam!.passages.find(passage=>passage.question_numbers.includes(p.number))!.number}))};
 await page.reload();await expect(page.getByText("Time expired · Academic Reading",{exact:true})).toBeVisible();
 for(const passage of attempt.exam!.passages)await expect(map.getByRole("region",{name:`Passage ${passage.number}`,exact:true}).getByRole("link")).toHaveCount(passage.question_numbers.length);
 expect(backend.events).toEqual([]);
});

test("Result V2: unfinished attempt never requests verdicts or exposes a map",async({page,context})=>{
 await releaseBackend(context);let resultRequests=0;
 await page.route(`**/api/alua/reading/attempts/${attemptId}/result`,route=>{resultRequests++;return route.fulfill({status:403})});
 await page.goto(`${path}/result`);await expect(page.getByRole("heading",{name:"This test is still in progress."})).toBeVisible();
 expect(resultRequests).toBe(0);await expect(page.getByRole("link",{name:/^Question \d+,/})).toHaveCount(0);
});
