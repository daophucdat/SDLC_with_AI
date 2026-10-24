// SourcePanel (T305.2 → T305.4): the cited page next to the answer, excerpt highlighted, Esc to close,
// previous / next page, #src=<docId>:<page> in the URL, "removed" state on 404 (EC-16).
import { useEffect, useRef, useState } from "react";
import { documentFileUrl } from "../api-client/documents";
import { fmt, vi } from "../i18n/vi";
import { useChatStore } from "../state/chatStore";
import type { SourceRef } from "../state/chatStore";
import { Button, Spinner } from "../ui";
import { findExcerpt, openPdf, PdfHttpError } from "./pdf";
import type { PdfDoc } from "./pdf";
import "./source.css";

type Status = "loading" | "ready" | "removed" | "error";

export default function SourcePanel({ source }: { source: SourceRef }) {
  const openSource = useChatStore((s) => s.openSource);
  const markRemoved = useChatStore((s) => s.markRemoved);
  const [doc, setDoc] = useState<PdfDoc | null>(null);
  const [status, setStatus] = useState<Status>("loading");
  const [page, setPage] = useState(source.page);
  const [highlighted, setHighlighted] = useState(true);
  const canvas = useRef<HTMLCanvasElement>(null);
  const textLayer = useRef<HTMLDivElement>(null);
  const body = useRef<HTMLDivElement>(null);
  const closeBtn = useRef<HTMLButtonElement>(null);

  // a new citation in the same document only changes the page; another document reloads (AC-305.2)
  useEffect(() => setPage(source.page), [source.page, source.index, source.turnKey]);

  useEffect(() => {
    let cancelled = false;
    let opened: PdfDoc | null = null;
    setStatus("loading");
    setDoc(null);
    openPdf(documentFileUrl(source.documentId))
      .then((d) => {
        if (cancelled) return d.destroy();
        opened = d;
        setDoc(d);
      })
      .catch((e) => {
        if (cancelled) return;
        if (e instanceof PdfHttpError && e.status === 404) {
          setStatus("removed");
          markRemoved([source.documentId]);
        } else setStatus("error");
      });
    return () => {
      cancelled = true;
      opened?.destroy(); // T305.2: free the PDFDocumentProxy when the panel closes or switches file
    };
  }, [source.documentId, markRemoved]);

  useEffect(() => {
    if (!doc || !canvas.current || !textLayer.current) return;
    let cancelled = false;
    const width = Math.max(280, (body.current?.clientWidth ?? 440) - 40);
    doc
      .renderPage(page, canvas.current, textLayer.current, width)
      .then((items) => {
        if (cancelled) return;
        setStatus("ready");
        const hits =
          page === source.page
            ? findExcerpt(
                items.map((el) => el.textContent ?? ""),
                source.excerpt,
              )
            : [];
        hits.forEach((i) => items[i].classList.add("highlight"));
        setHighlighted(page !== source.page || hits.length > 0);
        if (hits.length) items[hits[0]].scrollIntoView?.({ block: "center" });
        doc.prefetch(page - 1);
        doc.prefetch(page + 1);
      })
      .catch(() => !cancelled && setStatus("error"));
    return () => {
      cancelled = true;
    };
  }, [doc, page, source.page, source.excerpt]);

  useEffect(() => {
    try {
      history.replaceState(null, "", `#src=${source.documentId}:${page}`);
    } catch {
      /* ignore */
    }
  }, [source.documentId, page]);

  useEffect(() => {
    closeBtn.current?.focus();
  }, [source.documentId]);

  const close = () => {
    openSource(null);
    try {
      history.replaceState(null, "", window.location.pathname + window.location.search);
    } catch {
      /* ignore */
    }
  };

  const total = doc?.numPages ?? 0;
  return (
    <aside
      className="source-panel"
      aria-label={vi.source.label}
      onKeyDown={(e) => {
        if (e.key === "Escape") close();
      }}
    >
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
      <div className="source-body" ref={body}>
        {status === "removed" && <div className="source-status">{vi.source.removed}</div>}
        {status === "error" && <div className="source-status">{vi.source.error}</div>}
        {status === "loading" && (
          <div className="source-status">
            <Spinner label={vi.source.loading} />
          </div>
        )}
        {status === "ready" && !highlighted && <p className="xs muted">{vi.source.notHighlighted}</p>}
        <div className="pdf-stage" hidden={status === "removed" || status === "error"}>
          <canvas ref={canvas} aria-label={fmt(vi.source.page, { page, total: total || "?" })} role="img" />
          <div className="textLayer" ref={textLayer} />
        </div>
      </div>
      <div className="source-foot">
        <div className="row">
          <Button aria-label={vi.source.prev} disabled={page <= 1 || !doc} onClick={() => setPage((p) => p - 1)}>
            ‹
          </Button>
          <Button aria-label={vi.source.next} disabled={!doc || page >= total} onClick={() => setPage((p) => p + 1)}>
            ›
          </Button>
        </div>
        {status !== "removed" && (
          <a className="btn btn-ghost" href={documentFileUrl(source.documentId)} target="_blank" rel="noopener">
            {vi.source.openFull}
          </a>
        )}
      </div>
    </aside>
  );
}
