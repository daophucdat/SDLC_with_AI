import { ApiError } from "../../api-client/http";
import type { UploadHandle } from "../../api-client/documents";
import { doc } from "../../test/utils";
import { createUploadQueue, MAX_PARALLEL, RETRY_DELAYS_MS } from "./uploadQueue";
import type { UploadEvent } from "./uploadQueue";

vi.mock("../../analytics/track", () => ({ track: vi.fn() }));

function pdf(name = "a.pdf", size = 1000) {
  const f = new File(["%PDF-1.7"], name, { type: "application/pdf" });
  Object.defineProperty(f, "size", { value: size });
  return f;
}

/** Fake uploader: each call returns a handle whose promise the test settles by hand. */
function fakeUploader() {
  const pending: { file: File; force: boolean; resolve: (d: unknown) => void; reject: (e: unknown) => void }[] = [];
  const upload = vi.fn((file: File, opts: { force?: boolean } = {}): UploadHandle => {
    let resolve!: (d: unknown) => void, reject!: (e: unknown) => void;
    const promise = new Promise<never>((res, rej) => {
      resolve = res as never;
      reject = rej;
    });
    pending.push({ file, force: !!opts.force, resolve, reject });
    return { promise, abort: () => reject(new ApiError({ status: 0, code: "ABORTED" })) };
  });
  return { upload, pending };
}

const flush = () => new Promise((r) => setTimeout(r, 0));

describe("upload queue (US-201)", () => {
  it("uploads at most 3 files in parallel; the rest wait their turn (AC-201.2)", async () => {
    const { upload, pending } = fakeUploader();
    const q = createUploadQueue(() => undefined, { upload, isOnline: () => true });
    q.getState().add(Array.from({ length: 10 }, (_, i) => pdf(`f${i}.pdf`)));

    expect(q.getState().items).toHaveLength(10);
    expect(upload).toHaveBeenCalledTimes(MAX_PARALLEL);
    expect(q.getState().items.filter((i) => i.state === "UPLOADING")).toHaveLength(3);

    pending[0].resolve(doc({ id: "x" }));
    await flush();
    expect(upload).toHaveBeenCalledTimes(4);
    expect(q.getState().items).toHaveLength(9);
  });

  it("rejects non-PDF and > 50 MB files on the client without uploading", () => {
    const events: UploadEvent[] = [];
    const { upload } = fakeUploader();
    const q = createUploadQueue((e) => events.push(e), { upload, isOnline: () => true });
    q.getState().add([new File(["x"], "anh.png", { type: "image/png" }), pdf("big.pdf", 51 * 1024 * 1024)]);
    expect(upload).not.toHaveBeenCalled();
    expect(events.map((e) => e.type === "rejected" && e.code)).toEqual(["FILE_NOT_PDF", "FILE_TOO_LARGE"]);
  });

  it("pauses on network loss, retries after 2/4/8 s, then fails with a manual retry (EC-04)", async () => {
    const { upload, pending } = fakeUploader();
    const scheduled: number[] = [];
    let runLater: (() => void) | null = null;
    const q = createUploadQueue(() => undefined, {
      upload,
      isOnline: () => true,
      schedule: (fn, ms) => {
        scheduled.push(ms);
        runLater = fn;
      },
    });
    q.getState().add([pdf()]);

    for (let i = 0; i < RETRY_DELAYS_MS.length; i++) {
      pending[i].reject(new ApiError({ status: 0, code: "NETWORK" }));
      await flush();
      expect(q.getState().items[0].state).toBe("PAUSED");
      runLater!();
      await flush();
    }
    pending[3].reject(new ApiError({ status: 0, code: "NETWORK" }));
    await flush();
    expect(scheduled).toEqual([2000, 4000, 8000]);
    expect(q.getState().items[0].state).toBe("UPLOAD_FAILED");

    q.getState().retry(q.getState().items[0].key);
    expect(q.getState().items[0].state).toBe("UPLOADING");
    expect(upload).toHaveBeenCalledTimes(5);
  });

  it("duplicate → waits for the user; confirming resends with force=true", async () => {
    const { upload, pending } = fakeUploader();
    const q = createUploadQueue(() => undefined, { upload, isOnline: () => true });
    q.getState().add([pdf()]);
    pending[0].reject(
      new ApiError({ status: 409, code: "DUPLICATE_DOCUMENT", existingId: "d-1", uploadedAt: "2026-10-01T00:00:00Z" }),
    );
    await flush();
    const item = q.getState().items[0];
    expect(item.state).toBe("DUPLICATE");
    expect(item.duplicateOf).toEqual({ existingId: "d-1", uploadedAt: "2026-10-01T00:00:00Z" });

    q.getState().confirmDuplicate(item.key);
    expect(pending[1].force).toBe(true);
  });

  it("a server 415 removes the row and reports it", async () => {
    const events: UploadEvent[] = [];
    const { upload, pending } = fakeUploader();
    const q = createUploadQueue((e) => events.push(e), { upload, isOnline: () => true });
    q.getState().add([pdf("doi-duoi.pdf")]);
    pending[0].reject(new ApiError({ status: 415, code: "FILE_NOT_PDF" }));
    await flush();
    expect(q.getState().items).toHaveLength(0);
    expect(events).toEqual([
      { type: "rejected", fileName: "doi-duoi.pdf", code: "FILE_NOT_PDF", retryAfter: undefined },
    ]);
  });

  it("waits while offline and starts when the browser comes back online", () => {
    const { upload } = fakeUploader();
    let online = false;
    const q = createUploadQueue(() => undefined, { upload, isOnline: () => online });
    q.getState().add([pdf()]);
    expect(upload).not.toHaveBeenCalled();
    online = true;
    q.getState().resumeAll();
    expect(upload).toHaveBeenCalledOnce();
  });
});
