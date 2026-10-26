// Helpers for the test cases of docs/test-cases.md (local stack, backend/tests/e2e_server.py).
import { expect } from "@playwright/test";
import type { CDPSession, Page, Route } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

export const DATA = path.resolve(__dirname, "../fixtures/data");
const SHOTS = path.resolve(__dirname, "../../reports/screenshots", process.env.E2E_RUN ?? "run");
export const file = (name: string) => path.join(DATA, name);

/** Login through the test IdP page (stand-in for the company IdP; OIDC state / nonce / PKCE still checked). */
export async function loginLocal(page: Page, user = "member") {
  await page.goto("/auth/login?returnTo=%2F");
  await page.locator(`#login-${user}`).click();
  await expect(page.getByRole("button", { name: "Đăng xuất" })).toBeVisible();
}

/** Named evidence screenshot, referenced from reports/test-report.md. */
export async function evidence(page: Page, tc: string) {
  fs.mkdirSync(SHOTS, { recursive: true });
  await page.screenshot({ path: path.join(SHOTS, `${tc}.png`), fullPage: false });
}

export const library = (page: Page) => page.getByRole("complementary", { name: "Kho tài liệu" });
export const row = (page: Page, name: string) => library(page).locator("li.doc", { hasText: name });

export async function pick(page: Page, names: string[]) {
  await page.getByTestId("file-input").setInputFiles(names.map(file));
}

export async function waitReady(page: Page, name: string, timeout = 30_000) {
  await expect(row(page, name).getByText("Sẵn sàng", { exact: true })).toBeVisible({ timeout });
}

/** Uploads the file unless it is already in the shared library, then waits for READY. */
export async function ensureReady(page: Page, name: string) {
  if ((await row(page, name).count()) === 0) await pick(page, [name]);
  await waitReady(page, name);
}

/** Number of upload XHRs started and the highest number in flight at once, counted **inside the page** at the
 * XMLHttpRequest level. Playwright's request / requestfinished events (and XHR "loadend") over-count by one: the
 * app starts the next upload as soon as the previous one has loaded — see docs/bugs.md, harness defect HD-1. */
export async function uploadMonitor(page: Page) {
  await page.evaluate(() => {
    const w = window as unknown as { __uploads?: { started: number; inFlight: number; maxInFlight: number } };
    if (w.__uploads) {
      Object.assign(w.__uploads, { started: 0, inFlight: 0, maxInFlight: 0 });
      return;
    }
    const stats = { started: 0, inFlight: 0, maxInFlight: 0 };
    w.__uploads = stats;
    const open = XMLHttpRequest.prototype.open;
    const send = XMLHttpRequest.prototype.send;
    XMLHttpRequest.prototype.open = function (this: XMLHttpRequest & { __upload?: boolean }, ...args: unknown[]) {
      this.__upload = args[0] === "POST" && /\/api\/v1\/documents(\?|$)/.test(String(args[1]));
      return (open as (...a: unknown[]) => void).apply(this, args);
    } as typeof XMLHttpRequest.prototype.open;
    XMLHttpRequest.prototype.send = function (this: XMLHttpRequest & { __upload?: boolean }, body) {
      if (this.__upload) {
        stats.started += 1;
        stats.inFlight += 1;
        stats.maxInFlight = Math.max(stats.maxInFlight, stats.inFlight);
        // done = readyState 4, which fires *before* "load": the app resolves its promise in onload and may start
        // the next upload in that same task, before "loadend" — counting on loadend over-counts by one (HD-1)
        let open = true;
        this.addEventListener("readystatechange", () => {
          if (open && this.readyState === 4) {
            open = false;
            stats.inFlight -= 1;
          }
        });
      }
      return send.call(this, body);
    };
  });
  return {
    read: () =>
      page.evaluate(() => {
        const s = (window as unknown as { __uploads: { started: number; maxInFlight: number } }).__uploads;
        return { started: s.started, maxInFlight: s.maxInFlight };
      }),
  };
}

/** Network conditions through the Chrome DevTools Protocol (Chromium only). `slow` throttles uploads so progress
 * can be watched — but Chromium only *simulates* it (the bytes reach the server at full speed, the response is held
 * back; HD-2), so it must not be used to cut a connection mid-upload. Use `dropUploads` for that. */
export async function network(page: Page): Promise<{ slow: (bytesPerSec: number) => Promise<void>; offline: (on: boolean) => Promise<void> }> {
  const cdp: CDPSession = await page.context().newCDPSession(page);
  await cdp.send("Network.enable");
  let upload = -1;
  const apply = (offline: boolean) =>
    cdp.send("Network.emulateNetworkConditions", { offline, latency: 0, downloadThroughput: -1, uploadThroughput: upload });
  return {
    slow: async (bytesPerSec) => {
      upload = bytesPerSec;
      await apply(false);
    },
    offline: async (on) => {
      await apply(on);
      await page.context().setOffline(on); // also fires the window online / offline events the app listens to
      if (!on) await apply(false); // setOffline(false) resets throttling: put it back
    },
  };
}

/** Network loss for uploads that never reach the server (AC-201.4): uploads are held in flight; `cut()` drops them
 * and every new one with ERR_INTERNET_DISCONNECTED and switches the browser offline; `restore()` lets them through. */
export async function dropUploads(page: Page) {
  let down = false;
  const held: Route[] = [];
  await page.route(/\/api\/v1\/documents(\?|$)/, async (route) => {
    if (route.request().method() !== "POST") return route.fallback();
    if (down) return route.abort("internetdisconnected");
    held.push(route); // in flight until the connection is cut
  });
  return {
    cut: async () => {
      down = true;
      await page.context().setOffline(true);
      for (const r of held.splice(0)) await r.abort("internetdisconnected");
    },
    restore: async () => {
      await page.unroute(/\/api\/v1\/documents(\?|$)/);
      await page.context().setOffline(false);
    },
  };
}

/** Text of each paragraph of the last answer, and whether each one contains a citation chip (AC-303.1). */
export async function paragraphsWithCitations(page: Page): Promise<{ text: string; cited: boolean }[]> {
  const answer = page.getByRole("article", { name: "Câu trả lời" }).last();
  return answer.locator(".answer-text").evaluate((el) => {
    const out: { text: string; cited: boolean }[] = [];
    let cur = { text: "", cited: false };
    for (const node of Array.from(el.childNodes)) {
      if (node.nodeType === Node.TEXT_NODE) {
        const parts = (node.textContent ?? "").split(/\n\s*\n/);
        parts.forEach((part, i) => {
          if (i > 0) {
            out.push(cur);
            cur = { text: "", cited: false };
          }
          cur.text += part;
        });
      } else if ((node as HTMLElement).classList?.contains("cite")) {
        cur.cited = true;
      }
    }
    out.push(cur);
    return out.filter((p) => p.text.trim().length > 0);
  });
}

export async function ask(page: Page, question: string) {
  const box = page.getByLabel("Câu hỏi về tài liệu");
  await expect(box).toBeEnabled();
  await box.fill(question);
  await box.press("Enter");
}

export const lastAnswer = (page: Page) => page.getByRole("article", { name: "Câu trả lời" }).last();

/** Captures the answer stream (SSE) inside the page: Playwright cannot always read a streamed response body. */
export async function captureAnswers(page: Page) {
  await page.addInitScript(() => {
    const w = window as unknown as { __sse: string[] };
    w.__sse = [];
    const original = window.fetch;
    window.fetch = async (...args: Parameters<typeof fetch>) => {
      const res = await original(...args);
      const url = String(args[0] instanceof Request ? args[0].url : args[0]);
      if (url.includes("/questions") && res.body) {
        const [mine, theirs] = res.body.tee();
        new Response(mine).text().then((t) => w.__sse.push(t));
        return new Response(theirs, { status: res.status, statusText: res.statusText, headers: res.headers });
      }
      return res;
    };
  });
}

export async function nextAnswerStream(page: Page, before: number): Promise<string> {
  await expect.poll(() => page.evaluate(() => (window as unknown as { __sse: string[] }).__sse.length)).toBeGreaterThan(before);
  return page.evaluate((i) => (window as unknown as { __sse: string[] }).__sse[i], before);
}

export const answerStreamCount = (page: Page) =>
  page.evaluate(() => (window as unknown as { __sse: string[] }).__sse.length);

/** Number of READY documents in the shared library — the N of "Không tìm thấy … trong N tài liệu hiện có". */
export async function readyCount(page: Page): Promise<number> {
  const res = await page.request.get("/api/v1/documents?limit=100");
  const body = (await res.json()) as { items: { status: string }[] };
  return body.items.filter((d) => d.status === "READY").length;
}
