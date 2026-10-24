import { api } from "../api-client/http";

// FE analytics events (dev_tasks.md §0.7). Props are an allow-list: sizes and counts only, never content.
type Events = {
  document_upload_started: { file_size_mb: number; batch_size: number };
  document_upload_failed: { reason: "not_pdf" | "too_large" | "network" | "password" | "corrupt" };
  citation_clicked: { citation_index: number; doc_removed: boolean };
  answer_copied: { with_sources: boolean };
};

export function track<N extends keyof Events>(name: N, props: Events[N]): void {
  // Analytics must never break the UI, so failures are ignored (EN-08).
  api("/api/v1/events", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, props }),
  }).catch(() => undefined);
}
