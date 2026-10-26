// US-201 — test cases TC-201-01 → TC-201-13 of docs/test-cases.md (expected results written there before running).
import { expect, test } from "@playwright/test";
import fs from "node:fs";
import {
  dropUploads,
  evidence,
  file,
  library,
  loginLocal,
  network,
  pick,
  row,
  uploadMonitor,
  waitReady,
} from "./tc-helpers";

test.describe.configure({ mode: "serial" });

test.beforeEach(async ({ page }) => {
  await loginLocal(page);
});

test("TC-201-01 [AC-201.1][H] chọn 1 PDF bằng nút Tải tài liệu → xuất hiện, Sẵn sàng, 3 trang", async ({ page }) => {
  await pick(page, ["HopDong_ABC.pdf"]);
  await expect(row(page, "HopDong_ABC.pdf")).toBeVisible({ timeout: 2_000 });
  await waitReady(page, "HopDong_ABC.pdf");
  await expect(row(page, "HopDong_ABC.pdf")).toContainText("3 trang");
  await expect(row(page, "HopDong_ABC.pdf")).toContainText("Bạn");
  await evidence(page, "TC-201-01");
});

test("TC-201-02 [AC-201.1][V] kéo-thả file tên tiếng Việt có dấu → tên giữ nguyên, Sẵn sàng", async ({ page }) => {
  const name = "Hợp đồng ABC – bản ký.pdf";
  const b64 = fs.readFileSync(file(name)).toString("base64");
  const dataTransfer = await page.evaluateHandle(
    ({ b64, name }) => {
      const bytes = Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));
      const dt = new DataTransfer();
      dt.items.add(new File([bytes], name, { type: "application/pdf" }));
      return dt;
    },
    { b64, name },
  );
  const zone = page.getByTestId("dropzone");
  await zone.dispatchEvent("dragover", { dataTransfer });
  await zone.dispatchEvent("drop", { dataTransfer });
  await expect(library(page).locator(".doc-name", { hasText: name })).toHaveText(name);
  await waitReady(page, name);
  await evidence(page, "TC-201-02");
});

test("TC-201-03 TC-201-04 [AC-201.1][B][P] PDF 49,5 MB: thấy % tiến độ tăng dần; Sẵn sàng ≤ 300 s", async ({ page }) => {
  const net = await network(page);
  await net.slow(4 * 1024 * 1024); // ~4 MB/s → ~12 s of visible progress
  const t0 = Date.now();
  await pick(page, ["Lon_49MB.pdf"]);
  const bar = page.getByRole("progressbar", { name: "Tiến độ tải Lon_49MB.pdf" });
  await expect(bar).toBeVisible();
  const seen: number[] = [];
  await expect
    .poll(
      async () => {
        const v = Number((await bar.getAttribute("aria-valuenow").catch(() => null)) ?? -1);
        if (v >= 0) seen.push(v);
        return seen.filter((x) => x > 0 && x < 100).length;
      },
      { timeout: 60_000, intervals: [250] },
    )
    .toBeGreaterThanOrEqual(3);
  await expect(row(page, "Lon_49MB.pdf")).toContainText(/Đang tải lên \d+%/);
  await evidence(page, "TC-201-03");
  const mid = seen.filter((x) => x > 0 && x < 100);
  expect(mid[mid.length - 1]).toBeGreaterThan(mid[0]); // the percentage rises
  await net.slow(-1);
  await waitReady(page, "Lon_49MB.pdf", 300_000);
  const seconds = (Date.now() - t0) / 1000;
  test.info().annotations.push({ type: "TC-201-04 measured", description: `${seconds.toFixed(1)} s to READY` });
  expect(seconds).toBeLessThanOrEqual(300);
  await expect(row(page, "Lon_49MB.pdf")).not.toContainText("vượt 50 MB");
  await evidence(page, "TC-201-04");
});

test("TC-201-05 [AC-201.2][H] chọn 10 PDF cùng lúc → 10 dòng, tối đa 3 tải song song, cả 10 Sẵn sàng", async ({ page }) => {
  const names = Array.from({ length: 10 }, (_, i) => `TaiLieu_${String(i + 1).padStart(2, "0")}.pdf`);
  const net = await network(page);
  await net.slow(2 * 1024 * 1024); // keep uploads overlapping long enough to observe the queue
  const uploads = await uploadMonitor(page);
  await pick(page, names);
  for (const n of names) await expect(row(page, n)).toBeVisible();
  await evidence(page, "TC-201-05-queue");
  await net.slow(-1);
  for (const n of names) await waitReady(page, n, 60_000);
  const u = await uploads.read();
  test.info().annotations.push({ type: "max uploads in flight", description: String(u.maxInFlight) });
  expect(u.started).toBe(10);
  expect(u.maxInFlight).toBeGreaterThanOrEqual(2); // the queue really ran in parallel…
  expect(u.maxInFlight).toBeLessThanOrEqual(3); // …but never more than 3 (T201.5)
  await evidence(page, "TC-201-05");
});

test("TC-201-06 [AC-201.2][V] 9 PDF hợp lệ + 1 PDF hỏng → 9 Sẵn sàng, 1 Lỗi có lý do, không ảnh hưởng nhau", async ({ page }) => {
  const good = Array.from({ length: 9 }, (_, i) => `TaiLieu_${i + 11}.pdf`);
  await pick(page, [...good, "Hong.pdf"]);
  for (const n of good) await waitReady(page, n, 60_000);
  await expect(row(page, "Hong.pdf").getByText("Lỗi", { exact: true })).toBeVisible({ timeout: 60_000 });
  await expect(row(page, "Hong.pdf")).toContainText("File bị hỏng hoặc không mở được.");
  await evidence(page, "TC-201-06");
});

test("TC-201-07 [AC-201.3][N] ảnh .png → từ chối ở trình duyệt, không có request tải lên", async ({ page }) => {
  const uploads = await uploadMonitor(page);
  await pick(page, ["anh.png"]);
  await expect(page.getByText("anh.png: Chỉ hỗ trợ file PDF.")).toBeVisible();
  await evidence(page, "TC-201-07");
  expect((await uploads.read()).started).toBe(0);
  await expect(row(page, "anh.png")).toHaveCount(0);
});

test("TC-201-08 [AC-201.3][B] PDF 50 MB + 1 KB → báo vượt 50 MB, không tải lên", async ({ page }) => {
  const uploads = await uploadMonitor(page);
  await pick(page, ["Qua_50MB.pdf"]);
  await expect(page.getByText("Qua_50MB.pdf: File vượt 50 MB. Hãy tách file hoặc liên hệ trưởng nhóm.")).toBeVisible();
  await evidence(page, "TC-201-08");
  expect((await uploads.read()).started).toBe(0);
  await expect(row(page, "Qua_50MB.pdf")).toHaveCount(0);
});

test("TC-201-09 [AC-201.3][N] file .doc đổi đuôi .pdf → máy chủ từ chối, không vào kho", async ({ page }) => {
  await pick(page, ["Word_doi_duoi.pdf"]);
  await expect(page.getByText("Word_doi_duoi.pdf: Chỉ hỗ trợ file PDF.")).toBeVisible();
  await evidence(page, "TC-201-09");
  await expect(row(page, "Word_doi_duoi.pdf")).toHaveCount(0);
});

test("TC-201-10 [AC-201.3][N] PDF 0 byte → bị từ chối kèm lý do", async ({ page }) => {
  await pick(page, ["Rong.pdf"]);
  await expect(page.getByText(/^Rong\.pdf: /)).toBeVisible();
  await evidence(page, "TC-201-10");
  await expect(row(page, "Rong.pdf")).toHaveCount(0);
});

test("TC-201-11 [AC-201.3][V] lô lẫn hợp lệ / không hợp lệ → chỉ file hợp lệ được tải", async ({ page }) => {
  await pick(page, ["BaoGia_XYZ.pdf", "anh.png", "Qua_50MB.pdf"]);
  await expect(page.getByText("anh.png: Chỉ hỗ trợ file PDF.")).toBeVisible();
  await expect(page.getByText(/^Qua_50MB\.pdf: File vượt 50 MB/)).toBeVisible();
  await evidence(page, "TC-201-11-rejected");
  await waitReady(page, "BaoGia_XYZ.pdf");
  await evidence(page, "TC-201-11");
});

test("TC-201-12 [AC-201.4][R] mất mạng giữa lúc tải → tạm dừng → có mạng lại tự tải tiếp", async ({ page }) => {
  const net = await dropUploads(page); // HD-2: cut the connection before the server has the file
  await pick(page, ["Lon_8MB_a.pdf"]);
  await expect(page.getByRole("progressbar", { name: "Tiến độ tải Lon_8MB_a.pdf" })).toBeVisible();
  await net.cut();
  await expect(row(page, "Lon_8MB_a.pdf")).toContainText("Tạm dừng — mất kết nối");
  await evidence(page, "TC-201-12-paused");
  await page.waitForTimeout(2_000);
  await net.restore();
  await waitReady(page, "Lon_8MB_a.pdf", 120_000);
  await expect(row(page, "Lon_8MB_a.pdf")).toHaveCount(1); // one file, not a copy
  await evidence(page, "TC-201-12");
});

test("TC-201-13 [AC-201.4][R] mất mạng quá 3 lần thử → Tải lên thất bại + Thử lại → Sẵn sàng", async ({ page }) => {
  const uploads = await uploadMonitor(page);
  const net = await dropUploads(page);
  await pick(page, ["Lon_8MB_b.pdf"]);
  await expect(page.getByRole("progressbar", { name: "Tiến độ tải Lon_8MB_b.pdf" })).toBeVisible();
  await net.cut();
  // retries after 2 s, 4 s, 8 s (T201.6) → 1 attempt + 3 retries, then UPLOAD_FAILED
  await expect(row(page, "Lon_8MB_b.pdf").getByText("Tải lên thất bại")).toBeVisible({ timeout: 40_000 });
  await expect(row(page, "Lon_8MB_b.pdf")).toContainText("Không tải lên được. Kiểm tra kết nối rồi thử lại.");
  const attempts = (await uploads.read()).started;
  test.info().annotations.push({ type: "upload attempts while offline", description: String(attempts) });
  expect(attempts).toBe(4); // 1 attempt + 3 retries, no more
  await expect(row(page, "Lon_8MB_b.pdf")).toHaveCount(1); // nothing reached the server
  await evidence(page, "TC-201-13-failed");
  await net.restore();
  await row(page, "Lon_8MB_b.pdf").getByRole("button", { name: "Tuỳ chọn cho Lon_8MB_b.pdf" }).click();
  await page.getByRole("menuitem", { name: "Thử lại" }).click();
  await waitReady(page, "Lon_8MB_b.pdf", 120_000);
  await expect(row(page, "Lon_8MB_b.pdf")).toHaveCount(1);
  await evidence(page, "TC-201-13");
});
