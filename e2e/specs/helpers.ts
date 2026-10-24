import { expect } from "@playwright/test";
import type { Page } from "@playwright/test";
import path from "node:path";

// Test accounts of infra/keycloak/realm-chatdocs.json (staging: same names, passwords from CI secrets).
export const USERS = {
  member: { username: "thu.ha", name: "Thu Hà Trần" },
  lead: { username: "quoc.bao", name: "Quốc Bảo Lê" },
  manager: { username: "giam.doc", name: "Giám Đốc Phạm" },
  outsider: { username: "ke.toan", name: "Văn A Nguyễn" },
} as const;

export const SAMPLE_DOCS = path.resolve(__dirname, "../../eval/datasets/sample/docs");

export async function login(page: Page, who: keyof typeof USERS, returnTo = "/") {
  await page.goto(`/auth/login?returnTo=${encodeURIComponent(returnTo)}`);
  await page.locator("#username").fill(USERS[who].username);
  await page.locator("#password").fill(process.env[`E2E_${who.toUpperCase()}_PASSWORD`] ?? "Test@1234");
  await page.locator("#kc-login").click();
}

export async function logout(page: Page) {
  await page.getByRole("button", { name: "Đăng xuất" }).click();
  await expect(page).toHaveURL(/\/login/);
}

/** Uploads a sample PDF (unless it is already in the shared library) and waits until it is READY. */
export async function ensureReady(page: Page, fileName: string) {
  const library = page.getByRole("complementary", { name: "Kho tài liệu" });
  const row = library.locator("li.doc", { hasText: fileName });
  if ((await row.count()) === 0) {
    await page.getByTestId("file-input").setInputFiles(path.join(SAMPLE_DOCS, fileName));
    const dialog = page.getByRole("alertdialog", { name: "File đã có trong kho" });
    if (await dialog.isVisible().catch(() => false)) await dialog.getByRole("button", { name: "Huỷ" }).click();
  }
  await expect(library.locator("li.doc", { hasText: fileName }).getByText("Sẵn sàng")).toBeVisible({ timeout: 300_000 });
}

export async function ask(page: Page, question: string) {
  const box = page.getByLabel("Câu hỏi về tài liệu");
  await expect(box).toBeEnabled();
  await box.fill(question);
  await box.press("Enter");
}

export const lastAnswer = (page: Page) => page.getByRole("article", { name: "Câu trả lời" }).last();
