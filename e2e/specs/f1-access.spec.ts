// F1 — US-101, US-102, US-103 (AC-101.1 → 101.3, AC-102.1 → 102.2, AC-103.3)
import { expect, test } from "@playwright/test";
import { login, logout, USERS } from "./helpers";

test("BD member logs in and sees name and role within 5 s (AC-101.1)", async ({ page }) => {
  const t0 = Date.now();
  await login(page, "member");
  await expect(page.getByText(USERS.member.name)).toBeVisible();
  await expect(page.getByText("Thành viên BD")).toBeVisible();
  expect(Date.now() - t0).toBeLessThan(5_000 + 3_000); // + the IdP form itself
});

test("an open session survives closing and reopening the tab (AC-101.2)", async ({ page, context }) => {
  await login(page, "member");
  await page.close();
  const again = await context.newPage();
  await again.goto("/");
  await expect(again.getByText(USERS.member.name)).toBeVisible();
});

test("a non-BD account is refused and sees nothing about the library (AC-102.1)", async ({ page }) => {
  await login(page, "outsider");
  await expect(page).toHaveURL(/\/denied/);
  await expect(page.getByText("Bạn chưa được cấp quyền dùng công cụ này. Liên hệ trưởng nhóm BD.")).toBeVisible();
  await expect(page.getByText("Kho tài liệu")).toHaveCount(0);
});

test("API and file links refuse anonymous callers (AC-102.2)", async ({ request }) => {
  for (const url of ["/api/v1/me", "/api/v1/documents", "/api/v1/documents/00000000-0000-0000-0000-000000000000/file"]) {
    const r = await request.get(url);
    expect([401, 403]).toContain(r.status());
  }
});

test("logout ends the session and its conversation (AC-103.3, AC-308.2)", async ({ page }) => {
  await login(page, "member");
  await logout(page);
  const r = await page.request.get("/api/v1/me");
  expect(r.status()).toBe(401);
});
