// DocumentItem (US-202 T202.4): icon, Badge, message per status / errorCode, ⋯ menu — as in the prototype.
import { useEffect, useRef, useState } from "react";
import type { DocumentDto } from "../../api-client/types";
import { fmt, vi } from "../../i18n/vi";
import { Badge, Button, ProgressBar } from "../../ui";
import type { BadgeTone } from "../../ui";
import type { UploadItem } from "./uploadQueue";

type ViewStatus = "READY" | "PROCESSING" | "UPLOADING" | "PAUSED" | "UPLOAD_FAILED" | "NO_TEXT" | "ERROR";

const LOOK: Record<ViewStatus, { icon: string; tone: BadgeTone }> = {
  READY: { icon: "📄", tone: "ready" },
  PROCESSING: { icon: "⏳", tone: "processing" },
  UPLOADING: { icon: "⬆️", tone: "processing" },
  PAUSED: { icon: "📶", tone: "warning" },
  UPLOAD_FAILED: { icon: "⛔", tone: "error" },
  NO_TEXT: { icon: "⚠️", tone: "warning" },
  ERROR: { icon: "⛔", tone: "error" },
};

export interface ItemAction {
  label: string;
  onSelect: () => void;
  danger?: boolean;
}

interface RowProps {
  id: string;
  name: string;
  status: ViewStatus;
  progress?: number;
  meta?: string[];
  message?: { text: string; tone: "warning" | "error" | "muted" };
  actions: ItemAction[];
}

function Row({ id, name, status, progress, meta = [], message, actions }: RowProps) {
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const look = LOOK[status];
  const label = vi.status[status];

  useEffect(() => {
    if (!open) return;
    menuRef.current?.querySelector("button")?.focus();
    const close = () => setOpen(false);
    document.addEventListener("click", close);
    return () => document.removeEventListener("click", close);
  }, [open]);

  return (
    <li className="doc" id={`doc-${id}`} title={name}>
      <span className="doc-icon" aria-hidden="true">
        {look.icon}
      </span>
      <div style={{ minWidth: 0 }}>
        <div className="doc-name">{name}</div>
        <div className="doc-meta">
          <Badge tone={look.tone}>{status === "UPLOADING" ? `${label} ${Math.round(progress ?? 0)}%` : label}</Badge>
          {meta.map((m) => (
            <span key={m}>{m}</span>
          ))}
        </div>
        {status === "UPLOADING" && (
          <ProgressBar value={progress ?? 0} label={fmt(vi.library.progress, { file: name })} />
        )}
        {message && <div className={`doc-msg ${message.tone}`}>{message.text}</div>}
      </div>
      {actions.length > 0 ? (
        <div className="menu-wrap">
          <Button
            variant="ghost"
            icon
            aria-label={fmt(vi.library.options, { file: name })}
            aria-haspopup="menu"
            aria-expanded={open}
            onClick={(e) => {
              e.stopPropagation();
              setOpen((o) => !o);
            }}
          >
            ⋯
          </Button>
          <div
            className="menu"
            role="menu"
            ref={menuRef}
            hidden={!open}
            onKeyDown={(e) => e.key === "Escape" && setOpen(false)}
          >
            {actions.map((a) => (
              <button
                key={a.label}
                type="button"
                role="menuitem"
                className={a.danger ? "danger" : undefined}
                onClick={() => {
                  setOpen(false);
                  a.onSelect();
                }}
              >
                {a.label}
              </button>
            ))}
          </div>
        </div>
      ) : (
        <span />
      )}
    </li>
  );
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "" : d.toLocaleDateString("vi-VN");
}

export function DocumentItem({
  doc,
  meId,
  onRetry,
  onRemove,
}: {
  doc: DocumentDto;
  meId: string;
  onRetry: (d: DocumentDto) => void;
  onRemove?: (d: DocumentDto) => void;
}) {
  const status = doc.status as ViewStatus;
  const meta = [
    ...(doc.pageCount ? [fmt(vi.library.pages, { n: doc.pageCount })] : []),
    `${doc.uploadedBy.id === meId ? vi.library.you : doc.uploadedBy.displayName} · ${formatDate(doc.uploadedAt)}`,
  ];
  let message: RowProps["message"];
  if (doc.status === "PROCESSING") message = { text: vi.library.processingHint, tone: "muted" };
  if (doc.status === "NO_TEXT") message = { text: vi.library.noTextHint, tone: "warning" };
  if (doc.status === "ERROR")
    message = { text: vi.processingErrors[doc.errorCode ?? "INTERNAL"] ?? vi.processingErrors.INTERNAL, tone: "error" };
  const actions: ItemAction[] =
    doc.status === "ERROR" ? [{ label: vi.library.retry, onSelect: () => onRetry(doc) }] : [];
  // AC-204.1: only the uploader or a lead sees "Gỡ khỏi kho" (the server checks again)
  if (doc.canRemove && onRemove && doc.status !== "UPLOADING")
    actions.push({ label: vi.removeDoc.action, onSelect: () => onRemove(doc), danger: true });
  return <Row id={doc.id} name={doc.fileName} status={status} meta={meta} message={message} actions={actions} />;
}

export function UploadingItem({
  item,
  onRetry,
  onDismiss,
}: {
  item: UploadItem;
  onRetry: (key: string) => void;
  onDismiss: (key: string) => void;
}) {
  const status: ViewStatus =
    item.state === "PAUSED" ? "PAUSED" : item.state === "UPLOAD_FAILED" ? "UPLOAD_FAILED" : "UPLOADING";
  const message: RowProps["message"] =
    item.state === "UPLOAD_FAILED" ? { text: vi.errors.NETWORK, tone: "error" } : undefined;
  const actions: ItemAction[] =
    item.state === "UPLOAD_FAILED"
      ? [
          { label: vi.library.retry, onSelect: () => onRetry(item.key) },
          { label: vi.library.dismiss, onSelect: () => onDismiss(item.key) },
        ]
      : [];
  return (
    <Row
      id={item.key}
      name={item.file.name}
      status={status}
      progress={item.state === "QUEUED" ? 0 : item.progress}
      message={message}
      actions={actions}
    />
  );
}
