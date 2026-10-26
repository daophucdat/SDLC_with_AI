// US-303 — test cases TC-303-01 → TC-303-10 of docs/test-cases.md (TC-303-05 is manual, on staging).
// `#noref` / `#badref` select the scripted answers of the fake LLM (backend/chatdocs/adapters/llm/fake.py):
// they are how the test environment produces an answer without / with invalid citations (AC-303.3).
import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";
import {
  answerStreamCount,
  ask,
  captureAnswers,
  ensureReady,
  evidence,
  lastAnswer,
  loginLocal,
  nextAnswerStream,
  paragraphsWithCitations,
  readyCount,
} from "./tc-helpers";

test.describe.configure({ mode: "serial" });

const PAYMENT = "Điều khoản thanh toán của hợp đồng ABC là gì?";
const TWO_DOCS = "Thanh toán hợp đồng ABC và đơn giá triển khai báo giá XYZ?";

test.beforeEach(async ({ page }) => {
  await captureAnswers(page);
  await loginLocal(page);
  await ensureReady(page, "HopDong_ABC.pdf");
  await ensureReady(page, "BaoGia_XYZ.pdf");
});

async function askAndWait(page: Page, question: string) {
  const before = await answerStreamCount(page);
  await ask(page, question);
  const sse = await nextAnswerStream(page, before);
  const done = /event: (done|error)\ndata: (\{.*\})/.exec(sse);
  return { sse, final: done ? { event: done[1], ...JSON.parse(done[2]) } : null };
}

async function sourceLines(page: Page) {
  return lastAnswer(page).locator(".sources li").allInnerTexts();
}

test("TC-303-01 TC-303-10 [AC-303.1][H][P] mỗi đoạn có trích dẫn; mục Nguồn 'Tên — trang X'; ≤ 30 s, phần đầu ≤ 5 s", async ({
  page,
}) => {
  const { final } = await askAndWait(page, PAYMENT);
  await expect(lastAnswer(page).getByRole("heading", { name: "Nguồn" })).toBeVisible();
  const paragraphs = await paragraphsWithCitations(page);
  test.info().annotations.push({ type: "paragraphs", description: JSON.stringify(paragraphs) });
  expect(paragraphs.length).toBeGreaterThanOrEqual(1);
  for (const p of paragraphs) expect(p.cited, `paragraph without citation: ${p.text}`).toBe(true);
  const lines = await sourceLines(page);
  expect(lines.some((l) => /HopDong_ABC\.pdf — trang 2/.test(l))).toBe(true);
  for (const l of lines) expect(l).toMatch(/^\d+\s*\S.+ — trang \d+/s);
  await evidence(page, "TC-303-01");
  // TC-303-10 — measured by the server and sent in the final SSE event (ADR-16)
  expect(final?.event).toBe("done");
  test.info().annotations.push({ type: "TC-303-10 measured", description: JSON.stringify(final) });
  expect(final!.latencyMs).toBeLessThanOrEqual(30_000);
  expect(final!.firstTokenMs).toBeLessThanOrEqual(5_000);
});

test("TC-303-02 [AC-303.1][V] câu cần 2 tài liệu → mỗi đoạn có trích dẫn, Nguồn có cả 2 tài liệu", async ({ page }) => {
  await askAndWait(page, TWO_DOCS);
  await expect(lastAnswer(page).getByRole("heading", { name: "Nguồn" })).toBeVisible();
  for (const p of await paragraphsWithCitations(page)) expect(p.cited, p.text).toBe(true);
  const lines = (await sourceLines(page)).join("\n");
  expect(lines).toContain("HopDong_ABC.pdf");
  expect(lines).toContain("BaoGia_XYZ.pdf");
  await evidence(page, "TC-303-02");
});

test("TC-303-03 [AC-303.1][V] câu hỏi tiếng Anh → trả lời tiếng Anh, vẫn đủ trích dẫn", async ({ page }) => {
  await askAndWait(page, "What are the payment terms of the ABC contract?");
  await expect(lastAnswer(page).locator(".answer-text")).toContainText("According to the documents");
  for (const p of await paragraphsWithCitations(page)) expect(p.cited, p.text).toBe(true);
  await expect(lastAnswer(page).getByRole("heading", { name: "Nguồn" })).toBeVisible();
  await evidence(page, "TC-303-03");
});

test("TC-303-04 [AC-303.2][H] mỗi chip mở đúng tài liệu, đúng trang, đoạn trích được tô sáng", async ({ page }) => {
  const keyword: Record<string, string> = { "HopDong_ABC.pdf": "30%", "BaoGia_XYZ.pdf": "500" };
  await askAndWait(page, TWO_DOCS);
  const chips = lastAnswer(page).locator(".answer-text button.cite");
  const count = await chips.count();
  expect(count).toBeGreaterThanOrEqual(2);
  for (let i = 0; i < count; i++) {
    const label = (await chips.nth(i).getAttribute("aria-label")) ?? "";
    const [, name, pageNo] = /Nguồn \d+: (.+), trang (\d+)/.exec(label) ?? [];
    await chips.nth(i).click();
    const panel = page.getByRole("complementary", { name: "Trang nguồn" });
    await expect(panel.locator(".source-file")).toHaveText(name);
    await expect(panel.getByText(new RegExp(`^Trang ${pageNo} / \\d+$`))).toBeVisible();
    const highlighted = panel.locator(".textLayer .highlight");
    await expect(highlighted.first()).toBeVisible();
    await expect(panel.locator(".textLayer")).toContainText(keyword[name]);
    await evidence(page, `TC-303-04-chip${i + 1}`);
    await page.keyboard.press("Escape");
    await expect(panel).toHaveCount(0);
  }
});

test("TC-303-06 [AC-303.3][N] LLM trả lời không có trích dẫn → 'không tìm thấy', không còn chữ của LLM", async ({ page }) => {
  const { final } = await askAndWait(page, `${PAYMENT} #noref`);
  expect(final).toMatchObject({ event: "done", status: "NOT_FOUND", reason: "INVALID_CITATIONS" });
  const answer = lastAnswer(page);
  const n = await readyCount(page); // TD-1: the library is shared with US-201 — N is read, not assumed to be 2
  expect(n).toBeGreaterThanOrEqual(2);
  await expect(answer.getByRole("heading", { name: `Không tìm thấy thông tin này trong ${n} tài liệu hiện có` })).toBeVisible();
  await expect(answer).toHaveClass(/not-found/);
  await expect(answer).not.toContainText("Theo tài liệu");
  await expect(answer.getByRole("heading", { name: "Nguồn" })).toHaveCount(0);
  await evidence(page, "TC-303-06");
});

test("TC-303-07 TC-303-08 [AC-303.3][N][R] trích dẫn số không tồn tại → 'không tìm thấy'; câu sau vẫn bình thường", async ({
  page,
}) => {
  const bad = await askAndWait(page, `${PAYMENT} #badref`);
  expect(bad.final).toMatchObject({ status: "NOT_FOUND", reason: "INVALID_CITATIONS" });
  await expect(lastAnswer(page).getByRole("heading", { name: /Không tìm thấy thông tin này/ })).toBeVisible();
  await expect(lastAnswer(page)).not.toContainText("[7]");
  await evidence(page, "TC-303-07");
  // TC-303-08: same conversation, a normal question
  const ok = await askAndWait(page, PAYMENT);
  expect(ok.final).toMatchObject({ event: "done", status: "COMPLETED" });
  await expect(lastAnswer(page).getByRole("heading", { name: "Nguồn" })).toBeVisible();
  for (const p of await paragraphsWithCitations(page)) expect(p.cited).toBe(true);
  await evidence(page, "TC-303-08");
});

test("TC-303-09 [AC-303.4][H] dữ liệu lưu: trang và đoạn trích lấy từ PDF, không lấy từ chữ LLM viết", async ({ page }) => {
  await askAndWait(page, PAYMENT);
  const conversationId = await page.evaluate(() => sessionStorage.getItem("chat.conversationId"));
  expect(conversationId).toBeTruthy();
  const turns = await (await page.request.get(`/api/v1/conversations/${conversationId}/questions`)).json();
  const last = turns[turns.length - 1];
  expect(last.answer.status).toBe("COMPLETED");
  const cite = last.answer.citations.find((c: { fileName: string }) => c.fileName === "HopDong_ABC.pdf");
  expect(cite).toBeTruthy();
  expect(cite.page).toBe(2); // payment clause is on page 2 of the generated contract
  // TD-2: the excerpt is the PDF text verbatim, including the PDF's no-break spaces (U+00A0) — compare words, the
  // way retrieval does (retrieval_service: " ".join(text.split()))
  const excerpt = String(cite.excerpt).split(/\s+/).join(" ");
  expect(excerpt).toContain("Thanh toán: khách hàng thanh toán 30%"); // text of the PDF page…
  expect(excerpt).not.toContain("Theo tài liệu"); // …not the sentence the LLM wrote
  expect(last.answer.text).toContain("Theo tài liệu");
  test.info().annotations.push({ type: "stored citation", description: JSON.stringify(cite) });
});
