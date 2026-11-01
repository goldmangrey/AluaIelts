import { test, expect } from "@playwright/test";

test("approved home, responsive grid, keyboard and Reading navigation", async ({ page, browserName }, info) => {
  const errors: string[] = [];
  const apiRequests: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("request", (request) => { if (request.url().includes("/api/v1/")) apiRequests.push(request.url()); });
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Practice tests." })).toBeVisible();
  const cards = page.getByRole("navigation", { name: "IELTS sections" }).getByRole("link");
  await expect(cards).toHaveCount(4);
  const first = await cards.nth(0).boundingBox();
  const second = await cards.nth(1).boundingBox();
  expect(first).not.toBeNull(); expect(second).not.toBeNull();
  if (info.project.name === "mobile") expect(second!.y).toBeGreaterThan(first!.y);
  else expect(second!.y).toBe(first!.y);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  // WebKit follows Safari’s default Option-Tab navigation for links.
  await page.keyboard.press(browserName === "webkit" ? "Alt+Tab" : "Tab");
  await expect(page.getByRole("link", { name: "Skip to content" })).toBeFocused();
  expect(apiRequests).toEqual([]);
  await page.getByRole("link", { name: /02 Reading Practice tests/ }).click();
  await expect(page).toHaveURL(/\/reading$/);
  await expect(page.getByRole("heading", { name: "Reading." })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Practice tests aren’t available yet." })).toBeVisible();
  expect(errors).toEqual([]);
});

test("unfinished sections contain only coming soon and a way back", async ({ page }) => {
  for (const section of ["Listening", "Writing", "Speaking"]) {
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
