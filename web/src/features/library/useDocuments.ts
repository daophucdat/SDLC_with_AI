// useDocuments (US-202 T202.3, T202.5, US-205 T205.2, US-204 T204.5): poll every 3 s while something is processing,
// never while the tab is hidden; report status transitions (→ toast) and documents that left the library
// (→ their citations are marked removed). Transitions are only tracked on the unfiltered list.
import { useQuery } from "@tanstack/react-query";
import { useEffect, useRef } from "react";
import { listDocuments } from "../../api-client/documents";
import type { DocumentDto } from "../../api-client/types";

export const POLL_MS = 3000;
export const FILTER_MIN = 2;
export const documentsKey = (q: string) => ["documents", q.trim().length >= FILTER_MIN ? q.trim() : ""] as const;

const busy = (d: DocumentDto) => d.status === "PROCESSING" || d.status === "UPLOADING";

export interface DocumentWatchers {
  onReady?: (doc: DocumentDto) => void;
  onNoText?: (doc: DocumentDto) => void;
  onGone?: (documentIds: string[]) => void;
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
    const items = query.data?.items;
    if (!items || !unfiltered || query.isPlaceholderData) return;
    const prev = previous.current;
    if (prev) {
      for (const d of items) {
        const before = prev.get(d.id);
        if (before === "PROCESSING" && d.status === "READY") watchersRef.current.onReady?.(d);
        if (before === "PROCESSING" && d.status === "NO_TEXT") watchersRef.current.onNoText?.(d);
      }
      const now = new Set(items.map((d) => d.id));
      const gone = [...prev.keys()].filter((id) => !now.has(id));
      if (gone.length && !query.data?.nextCursor) watchersRef.current.onGone?.(gone);
    }
    previous.current = new Map(items.map((d) => [d.id, d.status]));
  }, [query.data, query.isPlaceholderData, unfiltered]);

  return query;
}
