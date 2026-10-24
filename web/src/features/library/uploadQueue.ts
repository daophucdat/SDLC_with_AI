// Upload queue (US-201 T201.5–T201.7): ≤ 3 parallel XHR uploads, per-file state, pause + retry 2/4/8 s on
// network loss, then UPLOAD_FAILED with a manual "Thử lại" (EC-04). 409 duplicates wait for a user decision.
import { create } from "zustand";
import { uploadDocument } from "../../api-client/documents";
import type { UploadHandle } from "../../api-client/documents";
import { ApiError } from "../../api-client/http";
import type { DocumentDto } from "../../api-client/types";
import { track } from "../../analytics/track";
import { precheck } from "./validation";

export const MAX_PARALLEL = 3;
export const RETRY_DELAYS_MS = [2000, 4000, 8000];

export type UploadState = "QUEUED" | "UPLOADING" | "PAUSED" | "UPLOAD_FAILED" | "DUPLICATE";

export interface UploadItem {
  key: string;
  file: File;
  state: UploadState;
  progress: number;
  attempts: number;
  force: boolean;
  errorCode?: string;
  duplicateOf?: { existingId: string; uploadedAt: string };
}

/** Outcomes the UI reacts to with a toast or a refetch. */
export type UploadEvent =
  | { type: "rejected"; fileName: string; code: string; retryAfter?: number }
  | { type: "accepted"; doc: DocumentDto };

interface Deps {
  upload: typeof uploadDocument;
  schedule: (fn: () => void, ms: number) => void;
  isOnline: () => boolean;
}

interface QueueState {
  items: UploadItem[];
  add: (files: File[]) => void;
  retry: (key: string) => void;
  confirmDuplicate: (key: string) => void;
  dismiss: (key: string) => void;
  resumeAll: () => void;
}

const REASON: Record<string, "not_pdf" | "too_large" | "network"> = {
  FILE_NOT_PDF: "not_pdf",
  FILE_TOO_LARGE: "too_large",
  NETWORK: "network",
};

let seq = 0;

export function createUploadQueue(onEvent: (e: UploadEvent) => void, deps: Partial<Deps> = {}) {
  const d: Deps = {
    upload: uploadDocument,
    schedule: (fn, ms) => void setTimeout(fn, ms),
    isOnline: () => navigator.onLine,
    ...deps,
  };
  const handles = new Map<string, UploadHandle>();

  return create<QueueState>((set, get) => {
    const patch = (key: string, p: Partial<UploadItem>) =>
      set((s) => ({ items: s.items.map((it) => (it.key === key ? { ...it, ...p } : it)) }));
    const remove = (key: string) => set((s) => ({ items: s.items.filter((it) => it.key !== key) }));

    const pump = () => {
      const { items } = get();
      let running = items.filter((it) => it.state === "UPLOADING").length;
      for (const it of items) {
        if (running >= MAX_PARALLEL) break;
        if (it.state === "QUEUED") {
          running++;
          start(it.key);
        }
      }
    };

    const fail = (it: UploadItem, code: string) => {
      track("document_upload_failed", { reason: REASON[code] ?? "network" });
      patch(it.key, { state: "UPLOAD_FAILED", errorCode: code });
    };

    const start = (key: string) => {
      const it = get().items.find((x) => x.key === key);
      if (!it) return;
      patch(key, { state: "UPLOADING", progress: 0, errorCode: undefined });
      const h = d.upload(it.file, { force: it.force, onProgress: (p) => patch(key, { progress: p }) });
      handles.set(key, h);
      h.promise
        .then((doc) => {
          remove(key);
          onEvent({ type: "accepted", doc });
        })
        .catch((err: unknown) => {
          const code = err instanceof ApiError ? err.code : "NETWORK";
          const cur = get().items.find((x) => x.key === key) ?? it;
          if (code === "ABORTED") return;
          if (code === "NETWORK") {
            if (cur.attempts >= RETRY_DELAYS_MS.length) {
              fail(cur, "NETWORK");
            } else {
              patch(key, { state: "PAUSED", attempts: cur.attempts + 1 });
              d.schedule(() => {
                const now = get().items.find((x) => x.key === key);
                if (now?.state === "PAUSED") {
                  patch(key, { state: "QUEUED" });
                  pump();
                }
              }, RETRY_DELAYS_MS[cur.attempts]);
            }
          } else if (code === "DUPLICATE_DOCUMENT" && err instanceof ApiError) {
            patch(key, {
              state: "DUPLICATE",
              duplicateOf: {
                existingId: String(err.problem.existingId ?? ""),
                uploadedAt: String(err.problem.uploadedAt ?? ""),
              },
            });
          } else {
            const retryAfter = err instanceof ApiError ? Number(err.problem.retryAfter) || undefined : undefined;
            if (code === "FILE_NOT_PDF" || code === "FILE_TOO_LARGE")
              track("document_upload_failed", { reason: REASON[code] });
            remove(key);
            onEvent({ type: "rejected", fileName: it.file.name, code, retryAfter });
          }
        })
        .finally(() => {
          handles.delete(key);
          pump();
        });
    };

    return {
      items: [],
      add: (files) => {
        const accepted: UploadItem[] = [];
        for (const file of files) {
          const reject = precheck(file);
          if (reject) {
            track("document_upload_failed", { reason: REASON[reject] });
            onEvent({ type: "rejected", fileName: file.name, code: reject });
            continue;
          }
          accepted.push({ key: `u${++seq}`, file, state: "QUEUED", progress: 0, attempts: 0, force: false });
        }
        if (!accepted.length) return;
        for (const it of accepted) {
          track("document_upload_started", {
            file_size_mb: Math.round((it.file.size / 1048576) * 10) / 10,
            batch_size: accepted.length,
          });
        }
        set((s) => ({ items: [...s.items, ...accepted] }));
        if (d.isOnline()) pump();
      },
      retry: (key) => {
        patch(key, { state: "QUEUED", attempts: 0 });
        pump();
      },
      confirmDuplicate: (key) => {
        patch(key, { state: "QUEUED", force: true, duplicateOf: undefined });
        pump();
      },
      dismiss: (key) => {
        handles.get(key)?.abort();
        remove(key);
        pump();
      },
      resumeAll: () => {
        set((s) => ({ items: s.items.map((it) => (it.state === "PAUSED" ? { ...it, state: "QUEUED" } : it)) }));
        pump();
      },
    };
  });
}

export type UploadQueueStore = ReturnType<typeof createUploadQueue>;
