// SourcePanel (T305.2 → T305.4): the cited page next to the answer, excerpt highlighted, Esc to close,
// previous / next page, #src=<docId>:<page> in the URL, "removed" state on 404 (EC-16).
import { useEffect, useRef, useState } from "react";
import type { RefObject } from "react";
import { documentFileUrl } from "../api-client/documents";
import { fmt, vi } from "../i18n/vi";
import { useChatStore } from "../state/chatStore";
import type { SourceRef } from "../state/chatStore";
import { Button, Spinner } from "../ui";
import { findExcerpt, openPdf, PdfHttpError } from "./pdf";
import type { PdfDoc } from "./pdf";
import "./source.css";

type Status = "loading" | "ready" | "removed" | "error";

function replaceHash(hash: string): void {
  try {
    history.replaceState(null, "", hash || window.location.pathname + window.location.search);
  } catch {
    /* history not available (sandboxed frame): the panel still works */
  }
}

/** Opens the PDF of a document (by Range, see pdf.ts) and frees it when the document changes or the panel closes. */
function usePdf(documentId: string, setStatus: (s: Status) => void): PdfDoc | null {
  const markRemoved = useChatStore((s) => s.markRemoved);
  const [doc, setDoc] = useState<PdfDoc | null>(null);
  useEffect(() => {
    let cancelled = false;
    let opened: PdfDoc | null = null;
    setStatus("loading");
    setDoc(null);
    openPdf(documentFileUrl(documentId))
      .then((d) => {
        if (cancelled) return d.destroy();
        opened = d;
        setDoc(d);
      })
      .catch((e) => {
        if (cancelled) return;
        const removed = e instanceof PdfHttpError && e.status === 404;
        if (removed) markRemoved([documentId]); // EC-15: its citations are crossed out
        setStatus(removed ? "removed" : "error");
      });
    return () => {
      cancelled = true;
      opened?.destroy(); // T305.2: free the PDFDocumentProxy when the panel closes or switches file
    };
  }, [documentId, markRemoved, setStatus]);
  return doc;
}

/** T305.3: marks the text-layer items that contain the excerpt; returns whether anything was found. */
function highlightExcerpt(items: HTMLElement[], excerpt: string): boolean {
  const hits = findExcerpt(
    items.map((el) => el.textContent ?? ""),
    excerpt,
  );
  hits.forEach((i) => items[i].classList.add("highlight"));
  if (hits.length) items[hits[0]].scrollIntoView?.({ block: "center" });
  return hits.length > 0;
}

interface Stage {
  canvas: RefObject<HTMLCanvasElement>;
  textLayer: RefObject<HTMLDivElement>;
  body: RefObject<HTMLDivElement>;
}

function usePageRender(
  doc: PdfDoc | null,
  page: number,
  source: SourceRef,
  stage: Stage,
  onRendered: (status: Status, highlighted: boolean) => void,
): void {
  useEffect(() => {
    const { canvas, textLayer, body } = stage;
    if (!doc || !canvas.current || !textLayer.current) return;
    let cancelled = false;
    const width = Math.max(280, (body.current?.clientWidth ?? 440) - 40);
    doc
      .renderPage(page, canvas.current, textLayer.current, width)
      .then((items) => {
        if (cancelled) return;
        const cited = page === source.page;
        onRendered("ready", !cited || highlightExcerpt(items, source.excerpt));
        doc.prefetch(page - 1);
        doc.prefetch(page + 1);
      })
      .catch(() => !cancelled && onRendered("error", true));
    return () => {
      cancelled = true;
    };
  }, [doc, page, source.page, source.excerpt, stage, onRendered]);
}

function StatusMessage({ status, highlighted }: { status: Status; highlighted: boolean }) {
  if (status === "removed") return <div className="source-status">{vi.source.removed}</div>;
  if (status === "error") return <div className="source-status">{vi.source.error}</div>;
  if (status === "loading") {
    return (
      <div className="source-status">
        <Spinner label={vi.source.loading} />
      </div>
    );
  }
  return highlighted ? null : <p className="xs muted">{vi.source.notHighlighted}</p>;
}

function SourceFooter(p: {
  page: number;
  total: number;
  ready: boolean;
  removed: boolean;
  documentId: string;
  onPage: (page: number) => void;
}) {
  return (
    <div className="source-foot">
      <div className="row">
        <Button aria-label={vi.source.prev} disabled={!p.ready || p.page <= 1} onClick={() => p.onPage(p.page - 1)}>
          ‹
        </Button>
        <Button
          aria-label={vi.source.next}
          disabled={!p.ready || p.page >= p.total}
          onClick={() => p.onPage(p.page + 1)}
        >
          ›
        </Button>
      </div>
      {!p.removed && (
        <a className="btn btn-ghost" href={documentFileUrl(p.documentId)} target="_blank" rel="noopener">
          {vi.source.openFull}
        </a>
      )}
    </div>
  );
}

export default function SourcePanel({ source }: { source: SourceRef }) {
  const openSource = useChatStore((s) => s.openSource);
  const [status, setStatus] = useState<Status>("loading");
  const [page, setPage] = useState(source.page);
  const [highlighted, setHighlighted] = useState(true);
  const [stage] = useState<Stage>(() => ({
    canvas: { current: null },
    textLayer: { current: null },
    body: { current: null },
  }));
  const closeBtn = useRef<HTMLButtonElement>(null);
  const doc = usePdf(source.documentId, setStatus);
  const [onRendered] = useState(() => (s: Status, h: boolean) => {
    setStatus(s);
    setHighlighted(h);
  });

  // a new citation in the same document only changes the page; another document reloads (AC-305.2)
  useEffect(() => setPage(source.page), [source.page, source.index, source.turnKey]);
  usePageRender(doc, page, source, stage, onRendered);
  useEffect(() => replaceHash(`#src=${source.documentId}:${page}`), [source.documentId, page]);
  useEffect(() => closeBtn.current?.focus(), [source.documentId]);

  const close = () => {
    openSource(null);
    replaceHash("");
  };

  const total = doc?.numPages ?? 0;
  const failed = status === "removed" || status === "error";
  return (
    <aside className="source-panel" aria-label={vi.source.label} onKeyDown={(e) => e.key === "Escape" && close()}>
      <div className="source-head">
        <div className="grow">
          <div className="source-file" title={source.fileName}>
            {source.fileName}
          </div>
          <div className="xs muted">{total ? fmt(vi.source.page, { page, total }) : ""}</div>
        </div>
        <Button ref={closeBtn} variant="ghost" icon aria-label={vi.source.close} onClick={close}>
          ✕
        </Button>
      </div>
      <div className="source-body" ref={stage.body}>
        <StatusMessage status={status} highlighted={highlighted} />
        <div className="pdf-stage" hidden={failed}>
          <canvas ref={stage.canvas} aria-label={fmt(vi.source.page, { page, total: total || "?" })} role="img" />
          <div className="textLayer" ref={stage.textLayer} />
        </div>
      </div>
      <SourceFooter
        page={page}
        total={total}
        ready={!!doc}
        removed={status === "removed"}
        documentId={source.documentId}
        onPage={setPage}
      />
    </aside>
  );
}
