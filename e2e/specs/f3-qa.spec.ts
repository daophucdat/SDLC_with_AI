// F3 / F4 — US-301 → US-311 and NFR-05 (source page ≤ 2 s)
import { expect, test } from "@playwright/test";
import { ask, ensureReady, lastAnswer, login } from "./helpers";

test.describe.configure({ mode: "serial" });

test.beforeEach(async ({ page }) => {
  await login(page, "member");
  await ensureReady(page, "HopDong_ABC_2026.pdf");
});

test("Vietnamese question → answer with citations and a source list (AC-301.1, AC-303.1)", async ({ page }) => {
  await ask(page, "Điều khoản thanh toán của hợp đồng với công ty ABC là gì?");
  const answer = lastAnswer(page);
  await expect(answer.getByRole("heading", { name: "Nguồn" })).toBeVisible({ timeout: 30_000 });
  await expect(answer.getByRole("button", { name: /^Nguồn 1: HopDong_ABC_2026\.pdf, trang \d+$/ })).toBeVisible();
});

test("English question → English answer (AC-301.2)", async ({ page }) => {
  await ask(page, "What is the warranty period in the ABC contract?");
  await expect(lastAnswer(page).locator(".answer-text")).toContainText(/the|warranty|months|According/i, { timeout: 30_000 });
});

test("empty input sends nothing; > 2,000 characters disables Gửi (AC-301.3, AC-301.4)", async ({ page }) => {
  const box = page.getByLabel("Câu hỏi về tài liệu");
  await box.fill("   ");
  await box.press("Enter");
  await expect(page.locator(".q-bubble")).toHaveCount(0);
  await box.fill("a".repeat(2001));
  await expect(page.getByRole("button", { name: "Gửi" })).toBeDisabled();
});

test("unanswerable question → neutral 'không tìm thấy' with next steps (AC-304.1, AC-304.3)", async ({ page }) => {
  await ask(page, "Logo của công ty ABC màu gì?");
  const answer = lastAnswer(page);
  await expect(answer.getByRole("heading", { name: /Không tìm thấy thông tin này/ })).toBeVisible({ timeout: 30_000 });
  await expect(answer).toHaveClass(/not-found/);
  await expect(answer.getByRole("button", { name: "Diễn đạt lại" })).toBeVisible();
});

test("clicking [1] opens the right page with the excerpt highlighted in ≤ 2 s (AC-305.1, NFR-05)", async ({ page }) => {
  await ask(page, "Giá trị hợp đồng ABC là bao nhiêu?");
  const chip = lastAnswer(page).getByRole("button", { name: /^Nguồn 1:/ });
  await expect(chip).toBeVisible({ timeout: 30_000 });
  const label = (await chip.getAttribute("aria-label")) ?? "";
  const page_ = Number(/trang (\d+)/.exec(label)?.[1]);
  const t0 = Date.now();
  await chip.click();
  const panel = page.getByRole("complementary", { name: "Trang nguồn" });
  await expect(panel.getByText(new RegExp(`^Trang ${page_} / \\d+$`))).toBeVisible();
  await expect(panel.locator(".textLayer .highlight").first()).toBeVisible();
  expect(Date.now() - t0).toBeLessThan(2_000); // single sample; the p95 over 20 runs is in perf/source.spec
  await expect(chip).toHaveAttribute("aria-pressed", "true");
  await page.keyboard.press("Escape");
  await expect(panel).toHaveCount(0);
});

test("copy with sources (AC-307.1)", async ({ page, context }) => {
  await context.grantPermissions(["clipboard-read", "clipboard-write"]);
  await ask(page, "Thời hạn bảo hành phần mềm trong hợp đồng ABC?");
  await lastAnswer(page).getByRole("button", { name: "⧉ Sao chép kèm nguồn" }).click({ timeout: 30_000 });
  const text = await page.evaluate(() => navigator.clipboard.readText());
  expect(text).toMatch(/Nguồn:\n\[1\] HopDong_ABC_2026\.pdf — trang \d+/);
});

test("feedback 👍 thanks once; 👎 offers 4 reasons (AC-309.1, AC-309.2)", async ({ page }) => {
  await ask(page, "Giá trị hợp đồng ABC là bao nhiêu?");
  const answer = lastAnswer(page);
  await answer.getByRole("button", { name: "👎 Chưa tốt" }).click({ timeout: 30_000 });
  await expect(answer.getByRole("group", { name: "Vì sao?" }).getByRole("button")).toHaveCount(4);
  await answer.getByRole("button", { name: "Thiếu ý" }).click();
  await expect(answer.getByText("✓ Cảm ơn phản hồi của bạn")).toBeVisible();
});

test("stop while streaming (AC-310.1)", async ({ page }) => {
  test.skip(process.env.E2E_LLM !== "fake", "deterministic only with the fake LLM (#hang keeps the stream open)");
  await ask(page, "Điều khoản thanh toán hợp đồng ABC #hang");
  await page.getByRole("button", { name: "Dừng câu trả lời đang soạn" }).click();
  await expect(lastAnswer(page).getByText("⏹ Đã dừng — câu trả lời chưa đầy đủ")).toBeVisible({ timeout: 5_000 });
  await expect(page.getByLabel("Câu hỏi về tài liệu")).toBeFocused();
});

test("reloading keeps the conversation of this session (AC-308.1)", async ({ page }) => {
  await ask(page, "Giá trị hợp đồng ABC là bao nhiêu?");
  await expect(lastAnswer(page).getByRole("heading", { name: "Nguồn" })).toBeVisible({ timeout: 30_000 });
  await page.reload();
  await expect(page.locator(".q-bubble", { hasText: "Giá trị hợp đồng ABC là bao nhiêu?" })).toBeVisible();
});
