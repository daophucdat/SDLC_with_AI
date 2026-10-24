// LibraryPanel + UploadDropzone (US-201 → US-206): pick or drag-drop many PDFs; shared library list with status;
// name filter (debounced, ≥ 2 characters); remove with confirmation (uploader or lead only).
import { useMutation, useQueryClient } from "@tanstack/react-query";
import type { QueryKey } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import type { DragEvent } from "react";
import { useStore } from "zustand";
import { removeDocument, retryDocument } from "../../api-client/documents";
import { ApiError } from "../../api-client/http";
import type { DocumentDto, DocumentListDto } from "../../api-client/types";
import { fmt, vi } from "../../i18n/vi";
import { useChatStore } from "../../state/chatStore";
import { useUiStore } from "../../state/uiStore";
import { Button, ConfirmDialog, EmptyState, Input, Spinner, useToast } from "../../ui";
import { DocumentItem, UploadingItem } from "./DocumentItem";
import { createUploadQueue } from "./uploadQueue";
import type { UploadEvent, UploadQueueStore } from "./uploadQueue";
import { FILTER_MIN, useDocuments } from "./useDocuments";

export const FILTER_DEBOUNCE_MS = 250;

function errorText(code: string, retryAfter?: number): string {
  return fmt(vi.errors[code] ?? vi.errors.INTERNAL, { retryAfter: retryAfter ?? 30 });
}

export function useUploadQueue(onEvent: (e: UploadEvent) => void): UploadQueueStore {
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;
  const [store] = useState(() => createUploadQueue((e) => onEventRef.current(e)));
  useEffect(() => {
    const resume = () => store.getState().resumeAll();
    window.addEventListener("online", resume);
    return () => window.removeEventListener("online", resume);
  }, [store]);
  return store;
}

function useDebounced<T>(value: T, ms: number): T {
  const [v, setV] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setV(value), ms);
    return () => clearTimeout(t);
  }, [value, ms]);
  return v;
}

export function LibraryPanel({ meId, expanded = false }: { meId: string; expanded?: boolean }) {
  const toast = useToast();
  const qc = useQueryClient();
  const [filterInput, setFilterInput] = useState("");
  const filter = useDebounced(filterInput, FILTER_DEBOUNCE_MS); // T203.2
  const [dragOver, setDragOver] = useState(false);
  const [toRemove, setToRemove] = useState<DocumentDto | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);
  const markRemoved = useChatStore((s) => s.markRemoved);

  const docs = useDocuments(filter);

  const queue = useUploadQueue((e) => {
    if (e.type === "accepted") qc.invalidateQueries({ queryKey: ["documents"] });
    else toast(`${e.fileName}: ${errorText(e.code, e.retryAfter)}`, "error");
  });
  const uploads = useStore(queue, (s) => s.items);
  const { add, retry, dismiss, confirmDuplicate } = queue.getState();
  const duplicate = uploads.find((u) => u.state === "DUPLICATE");

  const registerUpload = useUiStore((s) => s.registerUpload);
  useEffect(() => registerUpload(() => fileInput.current?.click(), add), [registerUpload, add]);

  const retryDoc = useMutation({
    mutationFn: (d: DocumentDto) => retryDocument(d.id),
    onError: (err) => {
      if (!(err instanceof ApiError && err.code === "INVALID_STATE"))
        toast(errorText(err instanceof ApiError ? err.code : "INTERNAL"), "error");
    },
    onSettled: () => qc.invalidateQueries({ queryKey: ["documents"] }),
  });

  // T204.4: optimistic — the row disappears at once, comes back if the server refuses
  const remove = useMutation({
    mutationFn: (d: DocumentDto) => removeDocument(d.id),
    onMutate: async (d) => {
      await qc.cancelQueries({ queryKey: ["documents"] });
      const snapshot = qc.getQueriesData<DocumentListDto>({ queryKey: ["documents"] });
      qc.setQueriesData<DocumentListDto>({ queryKey: ["documents"] }, (old) =>
        old ? { ...old, items: old.items.filter((x) => x.id !== d.id) } : old,
      );
      return { snapshot };
    },
    onSuccess: (_r, d) => {
      markRemoved([d.id]); // T204.5: citations of this document are crossed out
      toast(fmt(vi.removeDoc.done, { file: d.fileName }), "success");
    },
    onError: (err, _d, ctx) => {
      ctx?.snapshot.forEach(([key, data]: [QueryKey, DocumentListDto | undefined]) =>
        qc.setQueryData<DocumentListDto | undefined>(key, data),
      );
      toast(errorText(err instanceof ApiError ? err.code : "INTERNAL"), "error");
    },
    onSettled: () => qc.invalidateQueries({ queryKey: ["documents"] }),
  });

  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files.length) add(Array.from(e.dataTransfer.files));
  };

  const items = docs.data?.items ?? [];
  const visibleUploads = uploads.filter((u) => u.state !== "DUPLICATE");
  const filtering = filter.trim().length >= FILTER_MIN;
  const isEmpty = !docs.isPending && items.length === 0 && visibleUploads.length === 0;

  return (
    <aside className={`library${expanded ? " expanded" : ""}`} id="library" aria-label={vi.library.title}>
      <div className="library-head">
        <div className="library-title">
          <h2>
            {vi.library.title} {docs.data && !filtering && <span className="muted small">({items.length})</span>}
          </h2>
          <Button
            variant="primary"
            aria-label="Tải tài liệu PDF"
            title={vi.library.upload}
            onClick={() => fileInput.current?.click()}
          >
            <span aria-hidden="true">＋</span>
            <span className="upload-label">{vi.library.upload}</span>
          </Button>
          <input
            ref={fileInput}
            type="file"
            accept=".pdf,application/pdf"
            multiple
            className="sr-only"
            data-testid="file-input"
            tabIndex={-1}
            aria-hidden="true"
            onChange={(e) => {
              if (e.target.files?.length) add(Array.from(e.target.files));
              e.target.value = "";
            }}
          />
        </div>
        <div className="field">
          <label htmlFor="doc-filter" className="sr-only">
            Lọc theo tên
          </label>
          <Input
            id="doc-filter"
            type="search"
            title={vi.library.filter}
            placeholder={`🔍 ${vi.library.filter}`}
            value={filterInput}
            onChange={(e) => setFilterInput(e.target.value)}
          />
        </div>
      </div>
      <ul
        className={`doc-list${dragOver ? " drag-over" : ""}`}
        aria-live="polite"
        aria-busy={docs.isPending}
        data-testid="dropzone"
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
      >
        {visibleUploads.map((u) => (
          <UploadingItem key={u.key} item={u} onRetry={retry} onDismiss={dismiss} />
        ))}
        {items.map((d) => (
          <DocumentItem
            key={d.id}
            doc={d}
            meId={meId}
            onRetry={(doc) => retryDoc.mutate(doc)}
            onRemove={(doc) => setToRemove(doc)}
          />
        ))}
        {docs.isPending && (
          <li className="empty">
            <Spinner label="Đang tải danh sách" />
          </li>
        )}
        {isEmpty && (
          <li>
            {filtering ? (
              <EmptyState icon="🔍" title={vi.library.noMatch}>
                <Button variant="secondary" onClick={() => setFilterInput("")}>
                  {vi.removeDoc.clearFilter}
                </Button>
              </EmptyState>
            ) : (
              <EmptyState icon="📂" title={vi.library.emptyTitle}>
                {vi.library.emptyBody}
              </EmptyState>
            )}
          </li>
        )}
      </ul>
      <div className="library-foot">{vi.library.foot}</div>
      <ConfirmDialog
        open={!!duplicate}
        title={vi.library.duplicateTitle}
        body={fmt(vi.errors.DUPLICATE_DOCUMENT, {
          date: duplicate?.duplicateOf?.uploadedAt
            ? new Date(duplicate.duplicateOf.uploadedAt).toLocaleDateString("vi-VN")
            : "",
        })}
        confirmLabel={vi.library.uploadAnyway}
        danger={false}
        onConfirm={() => duplicate && confirmDuplicate(duplicate.key)}
        onCancel={() => duplicate && dismiss(duplicate.key)}
      />
      <ConfirmDialog
        open={!!toRemove}
        title={vi.removeDoc.title}
        body={fmt(vi.removeDoc.body, { file: toRemove?.fileName ?? "" })}
        confirmLabel={vi.removeDoc.confirm}
        onConfirm={() => {
          if (toRemove) remove.mutate(toRemove);
          setToRemove(null);
        }}
        onCancel={() => setToRemove(null)}
      />
    </aside>
  );
}
