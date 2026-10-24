// AnswerCard + CitationChip + SourceList + FeedbackControl (US-303, US-304, US-306, US-307, US-309).
// LLM text is rendered as React text nodes only — never innerHTML (T303.3).
import { useState } from "react";
import type { ReactNode } from "react";
import { track } from "../analytics/track";
import { ApiError } from "../api-client/http";
import { sendFeedback } from "../api-client/qa";
import type { CitationDto } from "../api-client/types";
import { fmt, vi } from "../i18n/vi";
import { isRemoved, useChatStore } from "../state/chatStore";
import { Button, Chip, Spinner, useToast } from "../ui";
import { citedIndices } from "./answerMachine";
import "./chat.css";
import type { ChatTurn } from "./answerMachine";

export interface AnswerCardProps {
  turn: ChatTurn;
  readyDocCount: number;
  streamRender: boolean;
  onRephrase: (question: string) => void;
  onUploadMore: () => void;
  onAskAgain: (turn: ChatTurn) => void;
}

function citeLabel(c: CitationDto, removed: boolean) {
  return fmt(vi.chat.citeLabel, { n: c.index, file: c.fileName, page: c.page }) + (removed ? vi.chat.citeRemoved : "");
}

function CitationChip({ turnKey, c }: { turnKey: string; c: CitationDto }) {
  const removedIds = useChatStore((s) => s.removedDocIds);
  const source = useChatStore((s) => s.source);
  const openSource = useChatStore((s) => s.openSource);
  const removed = isRemoved(c, removedIds);
  const active = !!source && source.turnKey === turnKey && source.index === c.index;
  return (
    <button
      type="button"
      className={`cite${removed ? " removed" : ""}`}
      aria-pressed={active}
      aria-label={citeLabel(c, removed)}
      aria-disabled={removed || undefined}
      title={removed ? vi.chat.removedTitle : `${c.fileName} — trang ${c.page}`}
      onClick={() => {
        track("citation_clicked", { citation_index: c.index, doc_removed: removed });
        if (removed) return; // EC-15: crossed out and not openable
        openSource({
          turnKey,
          index: c.index,
          documentId: c.documentId,
          fileName: c.fileName,
          page: c.page,
          excerpt: c.excerpt,
        });
      }}
    >
      {c.index}
    </button>
  );
}

/** Splits "… [1] … [2][3]" into text and chips. A number without a citation stays plain text. */
export function RichText({ turn, streaming }: { turn: ChatTurn; streaming: boolean }) {
  const byIndex = new Map(turn.citations.map((c) => [c.index, c]));
  const parts: ReactNode[] = turn.text.split(/(\[\d+\])/).map((part, i) => {
    const m = /^\[(\d+)\]$/.exec(part);
    const c = m ? byIndex.get(Number(m[1])) : undefined;
    return c ? <CitationChip key={i} turnKey={turn.key} c={c} /> : part;
  });
  return <div className={`answer-text${streaming ? " streaming" : ""}`}>{parts}</div>;
}

function SourceList({ turn }: { turn: ChatTurn }) {
  const removedIds = useChatStore((s) => s.removedDocIds);
  const openSource = useChatStore((s) => s.openSource);
  const byIndex = new Map(turn.citations.map((c) => [c.index, c]));
  const used = citedIndices(turn.text).filter((i) => byIndex.has(i));
  if (!used.length) return null;
  return (
    <div className="sources">
      <h3>{vi.chat.sources}</h3>
      <ol>
        {used.map((i) => {
          const c = byIndex.get(i)!;
          const removed = isRemoved(c, removedIds);
          return (
            <li key={i}>
              <button
                type="button"
                className="source-link"
                disabled={removed}
                aria-label={`Mở ${citeLabel(c, removed)}`}
                onClick={() => {
                  track("citation_clicked", { citation_index: i, doc_removed: removed });
                  openSource({
                    turnKey: turn.key,
                    index: i,
                    documentId: c.documentId,
                    fileName: c.fileName,
                    page: c.page,
                    excerpt: c.excerpt,
                  });
                }}
              >
                <span className={`cite${removed ? " removed" : ""}`} aria-hidden="true">
                  {i}
                </span>
                <span
                  style={removed ? { textDecoration: "line-through", color: "var(--color-text-muted)" } : undefined}
                >
                  {c.fileName} — trang {c.page}
                </span>
                {removed && <span className="xs muted">{vi.chat.removedTag}</span>}
              </button>
            </li>
          );
        })}
      </ol>
    </div>
  );
}

export function copyText(turn: ChatTurn): string {
  const byIndex = new Map(turn.citations.map((c) => [c.index, c]));
  const lines = citedIndices(turn.text)
    .filter((i) => byIndex.has(i))
    .map((i) => `[${i}] ${byIndex.get(i)!.fileName} — trang ${byIndex.get(i)!.page}`);
  return `${turn.text}\n\nNguồn:\n${lines.join("\n")}`;
}

function FeedbackControl({ turn }: { turn: ChatTurn }) {
  const toast = useToast();
  const patchTurn = useChatStore((s) => s.patchTurn);
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);

  const submit = async (value: "HELPFUL" | "NOT_HELPFUL", reason?: string) => {
    if (!turn.answerId || busy) return;
    setBusy(true);
    try {
      await sendFeedback(turn.answerId, value, reason);
      patchTurn(turn.key, { feedback: value });
      setOpen(false);
    } catch (e) {
      if (e instanceof ApiError && e.code === "ALREADY_SUBMITTED") patchTurn(turn.key, { feedback: value });
      else toast(vi.errors.INTERNAL, "error");
    } finally {
      setBusy(false);
    }
  };

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(copyText(turn));
      toast(vi.chat.copied, "success");
      track("answer_copied", { with_sources: true });
    } catch {
      toast(vi.chat.copyBlocked, "error"); // AC-307.2
    }
  };

  return (
    <div>
      <div className="answer-actions">
        {turn.feedback ? (
          <span className="xs muted" role="status">
            {vi.chat.thanks}
          </span>
        ) : (
          <>
            <Button variant="ghost" aria-pressed={false} disabled={busy} onClick={() => submit("HELPFUL")}>
              {vi.chat.helpful}
            </Button>
            <Button variant="ghost" aria-pressed={open} aria-expanded={open} onClick={() => setOpen((o) => !o)}>
              {vi.chat.notHelpful}
            </Button>
          </>
        )}
        <Button variant="ghost" onClick={copy}>
          {vi.chat.copy}
        </Button>
      </div>
      {open && !turn.feedback && (
        <div className="feedback-reasons" role="group" aria-label={vi.chat.why}>
          <span className="xs muted">{vi.chat.why}</span>
          {Object.entries(vi.chat.reasons).map(([code, label]) => (
            <Chip key={code} disabled={busy} onClick={() => submit("NOT_HELPFUL", code)}>
              {label}
            </Chip>
          ))}
        </div>
      )}
    </div>
  );
}

export function AnswerCard({
  turn,
  readyDocCount,
  streamRender,
  onRephrase,
  onUploadMore,
  onAskAgain,
}: AnswerCardProps) {
  const n = turn.readyDocCount ?? readyDocCount;
  const searching = turn.state === "SEARCHING" || (turn.state === "STREAMING" && !streamRender); // TQ-01 flag
  if (searching) {
    return (
      <article className="answer" aria-label={vi.chat.answer} aria-busy="true">
        <div className="answer-status">
          <Spinner />
          {fmt(vi.chat.searching, { n })}
        </div>
      </article>
    );
  }
  if (turn.state === "NOT_FOUND") {
    return (
      <article className="answer not-found" aria-label={vi.chat.answer}>
        <h3 style={{ fontSize: "var(--text-base)" }}>{fmt(vi.chat.notFoundTitle, { n })}</h3>
        <p className="small">{turn.replaced ? vi.chat.notFoundReplaced : vi.chat.notFoundBody}</p>
        <div className="row">
          <Button onClick={() => onRephrase(turn.question)}>{vi.chat.rephrase}</Button>
          <Button variant="ghost" onClick={onUploadMore}>
            {vi.chat.uploadMore}
          </Button>
        </div>
      </article>
    );
  }
  if (turn.state === "FAILED") {
    const code = turn.errorCode ?? "";
    const specific = ["AI_BUSY", "RATE_LIMITED", "NO_READY_DOCUMENTS"].includes(code);
    return (
      <article className="answer failed" aria-label={vi.chat.answer}>
        <p style={{ margin: "0 0 var(--space-3)" }}>
          {specific ? fmt(vi.errors[code], { retryAfter: 30 }) : vi.chat.failed}
        </p>
        <Button variant="primary" onClick={() => onAskAgain(turn)}>
          {vi.chat.retry}
        </Button>
      </article>
    );
  }
  return (
    <article className={`answer${turn.state === "INCOMPLETE" ? " incomplete" : ""}`} aria-label={vi.chat.answer}>
      {!!turn.processingDocCount && (
        <p className="xs muted">{fmt(vi.chat.processingNote, { n: turn.processingDocCount })}</p>
      )}
      <RichText turn={turn} streaming={turn.state === "STREAMING"} />
      {turn.state === "STOPPED" && <span className="answer-tag">{vi.chat.stopped}</span>}
      {turn.state === "INCOMPLETE" && (
        <>
          <span className="answer-tag">{vi.chat.incomplete}</span>
          <div className="answer-actions">
            <Button onClick={() => onAskAgain(turn)}>{vi.chat.askAgain}</Button>
          </div>
        </>
      )}
      {turn.state === "COMPLETED" && (
        <>
          <SourceList turn={turn} />
          <FeedbackControl turn={turn} />
        </>
      )}
    </article>
  );
}
