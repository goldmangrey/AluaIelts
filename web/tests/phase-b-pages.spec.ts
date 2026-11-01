import { test, expect } from "@playwright/test";

test("Reading settles without Web configuration and login is a real accessible form", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/reading");
  await expect(page.getByText("Loading practice tests…")).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "Practice tests aren’t available yet." })).toBeVisible();
  await page.getByRole("link", { name: "Log in", exact: true }).last().click();
  await expect(page).toHaveURL(/login\?next=%2Freading/);
  await page.getByLabel("Email", { exact: true }).fill("local@example.test");
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
