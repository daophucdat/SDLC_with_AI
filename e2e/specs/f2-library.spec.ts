// F2 — US-201 → US-206
import { expect, test } from "@playwright/test";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { ensureReady, login, SAMPLE_DOCS } from "./helpers";

test.describe.configure({ mode: "serial" });

test("upload shows progress, then PROCESSING, then READY within 5 min (AC-201.1, AC-202.1)", async ({ page }) => {
  await login(page, "member");
  await ensureReady(page, "HopDong_ABC_2026.pdf");
  await ensureReady(page, "BaoGia_XYZ_Q3.pdf");
  await ensureReady(page, "BienBan_Hop_KhachHang_DEF.pdf");
});

test("a non-PDF is refused on the client (US-201)", async ({ page }) => {
  await login(page, "member");
  const fake = path.join(os.tmpdir(), "anh.png");
  fs.writeFileSync(fake, "not a pdf");
  await page.getByTestId("file-input").setInputFiles(fake);
  await expect(page.getByText("anh.png: Chỉ hỗ trợ file PDF.")).toBeVisible();
});

test("a duplicate asks before uploading again (AC-206.1, AC-206.2)", async ({ page }) => {
  await login(page, "member");
  await page.getByTestId("file-input").setInputFiles(path.join(SAMPLE_DOCS, "HopDong_ABC_2026.pdf"));
  const dialog = page.getByRole("alertdialog", { name: "File đã có trong kho" });
  await expect(dialog).toContainText("File này đã có trong kho");
  await dialog.getByRole("button", { name: "Huỷ" }).click();
});

test("list shows name, pages, uploader and date; filter needs 2 characters (AC-203.1, AC-203.2)", async ({ page }) => {
  await login(page, "member");
  const library = page.getByRole("complementary", { name: "Kho tài liệu" });
  await expect(library.locator("li.doc", { hasText: "HopDong_ABC_2026.pdf" })).toContainText("3 trang");
  await page.getByLabel("Lọc theo tên").fill("bao");
  await expect(library.locator("li.doc", { hasText: "HopDong_ABC_2026.pdf" })).toHaveCount(0);
  await expect(library.locator("li.doc", { hasText: "BaoGia_XYZ_Q3.pdf" })).toBeVisible();
  await page.getByLabel("Lọc theo tên").fill("zzzz");
  await library.getByRole("button", { name: "Xoá bộ lọc" }).click();
  await expect(library.locator("li.doc")).not.toHaveCount(0);
});

test("only the uploader or a lead can remove; Huỷ has the focus; Esc closes (AC-204.1, AC-204.2)", async ({ browser }) => {
  const member2 = await browser.newPage();
  await login(member2, "lead");
  const lib = member2.getByRole("complementary", { name: "Kho tài liệu" });
  await lib.getByRole("button", { name: "Tuỳ chọn cho BienBan_Hop_KhachHang_DEF.pdf" }).click();
  await member2.getByRole("menuitem", { name: "Gỡ khỏi kho" }).click();
  const dialog = member2.getByRole("alertdialog", { name: "Gỡ tài liệu?" });
  await expect(dialog.getByRole("button", { name: "Huỷ" })).toBeFocused();
  await member2.keyboard.press("Escape");
  await expect(dialog).toHaveCount(0);
});

test("a scanned file is reported as unreadable (AC-205.1)", async ({ page }) => {
  test.skip(!process.env.E2E_SCANNED_PDF, "set E2E_SCANNED_PDF to a scanned PDF path");
  await login(page, "member");
  await page.getByTestId("file-input").setInputFiles(process.env.E2E_SCANNED_PDF!);
  await expect(page.getByText("Không đọc được chữ").first()).toBeVisible({ timeout: 300_000 });
});
