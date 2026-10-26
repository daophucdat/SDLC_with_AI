// useDocuments (US-202 T202.3, T202.5, US-205 T205.2, US-204 T204.5): poll every 3 s while something is processing,
// never while the tab is hidden; report status transitions (→ toast) and documents that left the library
// (→ their citations are marked removed). Transitions are only tracked on the unfiltered list.
import { useQuery } from "@tanstack/react-query";
import { useEffect, useRef } from "react";
import { listDocuments } from "../../api-client/documents";
import type { DocumentDto, DocumentListDto } from "../../api-client/types";

export const POLL_MS = 3000;
export const FILTER_MIN = 2;
export const documentsKey = (q: string) => ["documents", q.trim().length >= FILTER_MIN ? q.trim() : ""] as const;

const busy = (d: DocumentDto) => d.status === "PROCESSING" || d.status === "UPLOADING";

export interface DocumentWatchers {
  onReady?: (doc: DocumentDto) => void;
  onNoText?: (doc: DocumentDto) => void;
  onGone?: (documentIds: string[]) => void;
}

/** Compares two snapshots of the unfiltered list and calls the watchers for what changed. */
export function notifyChanges(prev: Map<string, string>, list: DocumentListDto, w: DocumentWatchers): void {
  for (const d of list.items) {
    if (prev.get(d.id) !== "PROCESSING") continue;
    if (d.status === "READY") w.onReady?.(d);
    if (d.status === "NO_TEXT") w.onNoText?.(d);
  }
  if (list.nextCursor) return; // a partial page cannot tell a removed document from one on the next page
  const now = new Set(list.items.map((d) => d.id));
  const gone = [...prev.keys()].filter((id) => !now.has(id));
  if (gone.length) w.onGone?.(gone);
}

export function useDocuments(q: string, watchers: DocumentWatchers = {}) {
  const query = useQuery({
    queryKey: documentsKey(q),
    queryFn: () => listDocuments({ q }),
    refetchInterval: (qq) => (qq.state.data?.items.some(busy) ? POLL_MS : false),
    refetchIntervalInBackground: false, // stops while document.hidden
    placeholderData: (prev) => prev,
  });

  const previous = useRef<Map<string, string> | null>(null);
  const watchersRef = useRef(watchers);
  watchersRef.current = watchers;
  const unfiltered = documentsKey(q)[1] === "";

  useEffect(() => {
    const list = query.data;
    if (!list || !unfiltered || query.isPlaceholderData) return;
    if (previous.current) notifyChanges(previous.current, list, watchersRef.current);
    previous.current = new Map(list.items.map((d) => [d.id, d.status]));
  }, [query.data, query.isPlaceholderData, unfiltered]);

  return query;
}
