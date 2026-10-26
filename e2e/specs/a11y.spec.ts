// T-EN12.3: axe on every screen and on the dialog / source panel (WCAG 2.1 AA, UX-S03)
import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
import { ask, ensureReady, lastAnswer, login } from "./helpers";

const axe = (page: import("@playwright/test").Page) => new AxeBuilder({ page } as unknown as ConstructorParameters<typeof AxeBuilder>[0]) // axe ships newer playwright-core types.withTags(["wcag2a", "wcag2aa", "wcag21aa"]);

test("/denied", async ({ page }) => {
  await login(page, "outsider");
  expect((await axe(page).analyze()).violations).toEqual([]);
});

test("/ workspace, confirm dialog and source panel", async ({ page }) => {
  await login(page, "member");
  await ensureReady(page, "HopDong_ABC_2026.pdf");
  expect((await axe(page).analyze()).violations).toEqual([]);

  await ask(page, "Giá trị hợp đồng ABC là bao nhiêu?");
  await lastAnswer(page).getByRole("button", { name: /^Nguồn 1:/ }).click({ timeout: 30_000 });
  await expect(page.getByRole("complementary", { name: "Trang nguồn" }).locator("canvas")).toBeVisible();
  expect((await axe(page).analyze()).violations).toEqual([]);

  const lib = page.getByRole("complementary", { name: "Kho tài liệu" });
  const menu = lib.getByRole("button", { name: /^Tuỳ chọn cho / }).first();
  if (await menu.count()) {
    await menu.click();
    const remove = page.getByRole("menuitem", { name: "Gỡ khỏi kho" });
    if (await remove.count()) {
      await remove.click();
      expect((await axe(page).analyze()).violations).toEqual([]);
      await page.keyboard.press("Escape");
    }
  }
});

test("/metrics", async ({ page }) => {
  await login(page, "lead", "/metrics");
  await expect(page.getByRole("tab", { name: "Số liệu sử dụng" })).toBeVisible();
  expect((await axe(page).analyze()).violations).toEqual([]);
});
