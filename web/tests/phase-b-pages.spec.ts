import { test, expect } from "@playwright/test";

test("Reading settles without Web configuration and login is a real accessible form", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/reading");
  await expect(page.getByText("Loading practice tests…")).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "Practice tests aren’t available yet." })).toBeVisible();
  await page.getByRole("link", { name: "Log in", exact: true }).last().click();
  await expect(page).toHaveURL(/login\?next=%2Freading/);
  await page.getByLabel("Email address", { exact: true }).fill("local@example.test");
  const password = page.getByLabel("Password", { exact: true });
  await password.fill("Local-Test-9284");
  await page.getByRole("button", { name: "Show password" }).click();
  await expect(password).toHaveAttribute("type", "text");
  await page.getByRole("button", { name: "Hide password" }).click();
  await expect(password).toHaveAttribute("type", "password");
  await page.getByRole("button", { name: "Log in", exact: true }).click();
  await expect(page.locator("p[role=alert]")).toContainText("isn’t configured");
  expect(errors).toEqual([]);
});

test("register/reset are real forms; missing configuration never claims success", async ({ page }) => {
  await page.goto("/register");
  await expect(page.getByLabel("Name", { exact: true })).toBeVisible();
  await expect(page.getByLabel("Password", { exact: true })).toHaveAttribute("autocomplete", "new-password");
  await page.goto("/forgot-password");
  await page.getByLabel("Email", { exact: true }).fill("local@example.test");
  await page.getByRole("button", { name: "Send reset instructions" }).click();
  await expect(page.locator("p[role=alert]")).toContainText("isn’t configured");
  await expect(page.getByText("Check your inbox.")).toHaveCount(0);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});


test("restored premium home uses the original four objects and login styling", async ({ page }, info) => {
  await page.emulateMedia({reducedMotion:"reduce"});
  await page.goto("/");
  const nav = page.getByRole("navigation", { name: "IELTS sections" });
  await expect(nav.getByRole("link")).toHaveCount(4);
  for (const section of ["listening", "reading", "writing", "speaking"]) {
    const image = nav.locator(`img[src="/images/home/${section}.webp"]`);
    await image.scrollIntoViewIfNeeded();
    await expect(image).toBeVisible();
    await expect.poll(() => image.evaluate((img: HTMLImageElement) => img.complete && img.naturalWidth > 700)).toBe(true);
    const card = image.locator("..");
    expect(await card.evaluate(el => getComputedStyle(el).borderRadius)).not.toBe("7px");
  }
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.getByRole("heading", {name:"Practice tests."}).click();
  await page.screenshot({ path: `.next/design-restoration/Home-${info.project.name}.png`, fullPage: true });
  await nav.getByRole("link", { name: "Reading, 3 passages, 40 questions", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Reading." })).toBeVisible();
  await page.screenshot({ path: `.next/design-restoration/Reading-${info.project.name}.png`, fullPage: true });
  await page.goto("/login?next=%2Flistening");
  await expect(page.getByRole("heading", { name: "Welcome back." })).toBeVisible();
  await expect(page.getByRole("button", { name: "Continue with Google", exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: /Continue with Apple/ })).toBeDisabled();
  await expect(page.getByLabel("Email address", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Connect Google safely" }).click();
  await expect(page.getByRole("status").filter({hasText:"Log in with your password"})).toBeVisible();
  await expect(page.getByRole("button", { name: "Continue with Google", exact: true })).toBeDisabled();
  await page.getByRole("button", { name: "Connect Google safely" }).click();
  await page.screenshot({ path: `.next/design-restoration/Login-${info.project.name}.png`, fullPage: true });
  await page.getByRole("link", { name: "Forgot password?", exact: true }).click();
  await expect(page).toHaveURL(/forgot-password\?next=%2Flistening/);
});
