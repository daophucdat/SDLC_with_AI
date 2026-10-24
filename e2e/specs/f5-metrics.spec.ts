// F5 / F6 — US-401, US-402
import { expect, test } from "@playwright/test";
import fs from "node:fs";
import { login } from "./helpers";

test("lead and manager see the weekly metrics with 4 / 8 / 12 weeks (AC-401.1)", async ({ page }) => {
  for (const who of ["lead", "manager"] as const) {
    await login(page, who, "/metrics");
    await expect(page.getByRole("tab", { name: "Số liệu sử dụng" })).toBeVisible();
    await page.getByLabel("Khoảng thời gian").selectOption("8");
    await expect(page.locator("tbody tr")).toHaveCount(8);
    await page.getByRole("button", { name: "Đăng xuất" }).click();
  }
});

test("a member has no menu entry and the API answers 403 (AC-401.2)", async ({ page }) => {
  await login(page, "member");
  await expect(page.getByRole("link", { name: "Số liệu" })).toHaveCount(0);
  const r = await page.request.get("/api/v1/metrics/weekly");
  expect(r.status()).toBe(403);
});

test("lead runs the test set and downloads the results (AC-402.1)", async ({ page }) => {
  test.skip(!process.env.E2E_EVALUATION, "flag 'evaluation' must be on in this environment");
  await login(page, "lead", "/metrics");
  await page.getByRole("tab", { name: "Nghiệm thu chất lượng" }).click();
  const tpl = await page.request.get("/api/v1/evaluations-template");
  const path = test.info().outputPath("mau.xlsx");
  fs.writeFileSync(path, await tpl.body());
  await page.getByLabel("File bộ câu hỏi").setInputFiles(path);
  await page.getByRole("button", { name: "Chạy nghiệm thu" }).click();
  await expect(page.getByRole("link", { name: "⬇ Tải kết quả (.xlsx)" })).toBeVisible({ timeout: 120_000 });
});
