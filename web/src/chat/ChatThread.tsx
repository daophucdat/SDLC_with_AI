// ChatThread (T301.5): empty library → big drop zone (EC-01); no question yet → 3 sample questions (EC-02);
// otherwise the turns. A separate polite live region announces only "started" / "finished" (T306.2).
import { useEffect, useRef, useState } from "react";
import type { DragEvent } from "react";
import { fmt, vi } from "../i18n/vi";
import { useChatStore } from "../state/chatStore";
import { useUiStore } from "../state/uiStore";
import { Button } from "../ui";
import { AnswerCard } from "./AnswerCard";
import type { ChatTurn } from "./answerMachine";

export interface ChatThreadProps {
  libraryEmpty: boolean;
  readyDocCount: number;
  canAsk: boolean;
  streamRender: boolean;
  announcement: string;
  onAsk: (question: string, opts?: { isSuggested?: boolean }) => void;
  onRephrase: (question: string) => void;
  onAskAgain: (turn: ChatTurn) => void;
}

export function ChatThread(p: ChatThreadProps) {
  const turns = useChatStore((s) => s.turns);
  const openPicker = useUiStore((s) => s.openPicker);
  const addFiles = useUiStore((s) => s.addFiles);
  const [dragOver, setDragOver] = useState(false);
  const bottom = useRef<HTMLDivElement>(null);
  const lastText = turns[turns.length - 1]?.text.length ?? 0;

  useEffect(() => {
    bottom.current?.scrollIntoView?.({ block: "end" });
  }, [turns.length, lastText]);

  let body;
  if (p.libraryEmpty && !turns.length) {
    const onDrop = (e: DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      if (e.dataTransfer.files.length) addFiles?.(Array.from(e.dataTransfer.files));
    };
    body = (
      <div
        className={`hero-drop${dragOver ? " drag-over" : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
      >
        <div className="empty-icon" aria-hidden="true">
          📥
        </div>
        <h2>{vi.chat.heroTitle}</h2>
        <p className="muted">{vi.chat.heroBody}</p>
        <Button variant="primary" size="lg" onClick={() => openPicker?.()}>
          {vi.chat.heroButton}
        </Button>
      </div>
    );
  } else if (!turns.length) {
    body = (
      <div className="empty">
        <div className="empty-icon" aria-hidden="true">
          💬
        </div>
        <h2>{p.readyDocCount ? fmt(vi.chat.emptyTitle, { n: p.readyDocCount }) : vi.chat.preparingTitle}</h2>
        <p>{p.readyDocCount ? vi.chat.emptyBody : vi.chat.preparingBody}</p>
        {p.readyDocCount > 0 && (
          <div className="suggestions">
            {vi.chat.suggestions.map((s) => (
              <button
                key={s}
                type="button"
                className="suggestion"
                disabled={!p.canAsk}
                onClick={() => p.onAsk(s, { isSuggested: true })}
              >
                {s}
              </button>
            ))}
          </div>
        )}
      </div>
    );
  } else {
    body = turns.map((t) => (
      <div key={t.key} style={{ display: "contents" }}>
        <div className="q-bubble">{t.question}</div>
        <AnswerCard
          turn={t}
          readyDocCount={p.readyDocCount}
          streamRender={p.streamRender}
          onRephrase={p.onRephrase}
          onUploadMore={() => openPicker?.()}
          onAskAgain={p.onAskAgain}
        />
      </div>
    ));
  }

  return (
    <div className="thread">
      <div className="thread-inner">
        {body}
        <div ref={bottom} />
      </div>
      <div className="sr-only" role="status" aria-live="polite">
        {p.announcement}
      </div>
    </div>
  );
}
