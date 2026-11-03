import { test, expect, type Page } from "@playwright/test";
async function select(page: Page, word: string) {
  await page.locator("[data-highlight-block]").evaluate((element, word) => {
    const node = element.firstChild!; const start = node.textContent!.indexOf(word);
    const range = document.createRange(); range.setStart(node, start); range.setEnd(node, start + word.length);
    window.getSelection()!.removeAllRanges(); window.getSelection()!.addRange(range);
  }, word);
}
test("selection loading, exact expression, cache, errors, dismissal and answer isolation", async ({ page }) => {
  let calls = 0;
  await page.route("**/api/translate", async route => {
    calls++;
    const input = route.request().postDataJSON();
    await new Promise(resolve => setTimeout(resolve, 250));
    const expression = input.selected === "forward" ? "looking forward to" : input.selected;
    if (expression === "evidence") { await route.fulfill({ status: 503, json: {} }); return; }
    await route.fulfill({ json: { expression, translation: "с нетерпением ждать" } });
  });
  await page.goto("/translate-qa");
  await expect(page.locator("main")).toHaveAttribute("data-ready", "true");
  await select(page, "forward");
  const card = page.getByRole("status", { name: "Перевод" });
  await expect(card).toContainText("Переводим");
  await expect(card).toContainText("looking forward to");
  await expect(card).toContainText("с нетерпением ждать");
  const box = await card.boundingBox(); const viewport = page.viewportSize()!;
  expect(box!.x).toBeGreaterThanOrEqual(0); expect(box!.x + box!.width).toBeLessThanOrEqual(viewport.width);
  await page.screenshot({ path: `test-results/translate-${viewport.width}.png` });
  await page.keyboard.press("Escape"); await expect(card).toHaveCount(0);
  await page.evaluate(() => window.getSelection()?.removeAllRanges()); await page.waitForTimeout(700);
  await select(page, "forward"); await expect(card).toContainText("looking forward to"); expect(calls).toBe(1);
  await page.getByRole("heading", { name: "Translation fixture" }).click(); await expect(card).toHaveCount(0);
  await select(page, "evidence"); await expect(card).toContainText("Не удалось");
  await page.getByRole("textbox", { name: "Answer" }).fill("my answer");
  await page.getByRole("textbox", { name: "Answer" }).selectText();
  await page.waitForTimeout(800); expect(calls).toBe(2); await expect(card).toHaveCount(0);
});
