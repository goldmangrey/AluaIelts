import { test, expect } from "@playwright/test";

test("home hero, four IELTS cards and retired Vocabulary routes", async ({ page, browserName }, info) => {
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  await page.goto("/");
  await expect(page.getByRole("heading", {name:"Don't just practise. Understand your mistakes."})).toBeVisible();
  await expect(page.getByText("Free forever", {exact:true})).toBeVisible();
  await expect(page.getByText("AI explanations", {exact:true})).toBeVisible();
  const cards = page.getByRole("navigation", {name:"IELTS sections"}).getByRole("link");
  await expect(cards).toHaveCount(4);
  await expect(page.locator('a[href*="vocabulary"]')).toHaveCount(0);
  const first=await cards.nth(0).boundingBox(), second=await cards.nth(1).boundingBox();
  expect(first).not.toBeNull(); expect(second).not.toBeNull();
  if(info.project.name==="mobile")expect(second!.y).toBeGreaterThan(first!.y);
  else expect(second!.y).toBe(first!.y);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await page.keyboard.press(browserName==="webkit"?"Alt+Tab":"Tab");
  await expect(page.getByRole("link",{name:"Skip to content"})).toBeFocused();
  for(const section of ["listening","reading","writing","speaking"]){
    await page.goto("/");
    await page.locator(`nav[aria-label="IELTS sections"] a[href="/${section}"]`).click();
    await expect(page).toHaveURL(new RegExp(`/${section}$`));
    await expect(page.locator("main")).toBeVisible();
  }
  for(const path of ["/vocabulary","/vocabulary/library","/vocabulary/intensive","/vocabulary/my","/vocabulary/sources","/vocabulary/word/lex_achievement_d52681089fc2"]){
    const response=await page.goto(path);expect(response?.status()).toBe(404);
  }
  expect(errors).toEqual([]);
});

test("unfinished sections contain only coming soon and a way back", async ({ page }) => {
  for (const section of ["Writing", "Speaking"]) {
    await page.goto(`/${section.toLowerCase()}`);
    await expect(page.getByRole("heading", { name: `${section}.` })).toBeVisible();
    await expect(page.getByText("Coming soon.", { exact: true })).toBeVisible();
    await page.getByRole("link", { name: "All sections" }).click();
    await expect(page).toHaveURL(/\/$/);
  }
});

test("book/test routes, real source numbering, no fake start or auth", async ({ page }) => {
  await page.goto("/reading/cambridge-12");
  await expect(page.getByRole("heading", { name: "Cambridge 12." })).toBeVisible();
  await page.goto("/reading/cambridge-12/cambridge-12-test-05");
  await expect(page.getByRole("heading", { name: "Academic Reading." })).toBeVisible();
  await expect(page.getByText("Test 5", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Start test" })).toHaveCount(0);
  for (const route of ["login", "register", "forgot-password", "profile"]) {
    await page.goto(`/${route}`);
    await expect(page.getByText(/Account access on the web is coming soon/)).toBeVisible();
    await expect(page.getByRole("textbox")).toHaveCount(0);
  }
  await page.goto("/reading/cambridge-18/cambridge-19-test-01");
  await expect(page.getByRole("heading", { name: "Page not found." })).toBeVisible();
  await page.goto("/missing-page");
  await expect(page.getByRole("heading", { name: "Page not found." })).toBeVisible();
});
