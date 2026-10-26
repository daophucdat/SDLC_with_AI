// QuestionComposer (T301.3, T310.3, T103.3): auto-growing textarea, Enter to send (not while an IME is composing),
// n/2000 counter, disabled with a reason, draft kept in sessionStorage — also across a session expiry (EC-17).
import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from "react";
import type { FormEvent, KeyboardEvent, RefObject } from "react";
import { vi } from "../i18n/vi";
import { Button } from "../ui";

export const MAX_CHARS = 2000;
export const WARN_CHARS = 1800;
export const DRAFT_KEY = "composer.draft";

function readDraft(): string {
  try {
    return sessionStorage.getItem(DRAFT_KEY) ?? "";
  } catch {
    return "";
  }
}

function writeDraft(v: string): void {
  try {
    if (v) sessionStorage.setItem(DRAFT_KEY, v);
    else sessionStorage.removeItem(DRAFT_KEY);
  } catch {
    /* storage unavailable */
  }
}

export interface ComposerHandle {
  focus: () => void;
  setText: (text: string) => void;
}

export interface QuestionComposerProps {
  disabledReason: string | null;
  streaming: boolean;
  followUpAvailable: boolean;
  onSubmit: (text: string, followUp: boolean) => void;
  onStop: () => void;
}

/** Enter sends; Shift+Enter is a new line; Enter that confirms an IME (Vietnamese Telex / VNI) composition is ignored. */
function isSendKey(e: KeyboardEvent<HTMLTextAreaElement>): boolean {
  return e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing && e.keyCode !== 229;
}

function useAutoGrow(area: RefObject<HTMLTextAreaElement>, text: string): void {
  useEffect(() => {
    const el = area.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, [area, text]);
}

function Counter({ count }: { count: number }) {
  const level = count > MAX_CHARS ? " over" : count > WARN_CHARS ? " near" : "";
  return (
    <span className={`counter${level}`} id="composer-counter" aria-live={level ? "polite" : undefined}>
      {count}/{MAX_CHARS}
    </span>
  );
}

function SendOrStop({ streaming, canSend, onStop }: { streaming: boolean; canSend: boolean; onStop: () => void }) {
  if (streaming) {
    return (
      <Button variant="secondary" aria-label={vi.chat.stopLabel} onClick={onStop}>
        {vi.chat.stop}
      </Button>
    );
  }
  return (
    <Button type="submit" variant="primary" disabled={!canSend}>
      {vi.chat.send}
    </Button>
  );
}

export const QuestionComposer = forwardRef<ComposerHandle, QuestionComposerProps>(function QuestionComposer(
  { disabledReason, streaming, followUpAvailable, onSubmit, onStop },
  ref,
) {
  const [text, setText] = useState(readDraft);
  const [followUp, setFollowUp] = useState(false);
  const area = useRef<HTMLTextAreaElement>(null);

  useImperativeHandle(ref, () => ({
    focus: () => area.current?.focus(),
    setText: (t: string) => {
      setText(t);
      area.current?.focus();
    },
  }));

  useEffect(() => writeDraft(text), [text]);
  useAutoGrow(area, text);

  const count = text.length;
  const over = count > MAX_CHARS;
  const reason = disabledReason ?? (over ? vi.chat.disabledTooLong : null);
  const canSend = !streaming && !reason && text.trim().length > 0;

  const submit = () => {
    if (!canSend) return; // empty / whitespace-only never sends (AC-301.3)
    onSubmit(text.trim(), followUpAvailable && followUp);
    setText("");
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (!isSendKey(e)) return;
    e.preventDefault();
    submit();
  };

  return (
    <div className="composer-wrap">
      <form
        className={`composer${disabledReason ? " disabled" : ""}`}
        autoComplete="off"
        onSubmit={(e: FormEvent) => {
          e.preventDefault();
          submit();
        }}
      >
        <label htmlFor="composer-input" className="sr-only">
          {vi.chat.label}
        </label>
        <div className="composer-box">
          <textarea
            id="composer-input"
            ref={area}
            rows={1}
            value={text}
            placeholder={vi.chat.placeholder}
            disabled={!!disabledReason}
            aria-describedby="composer-hint composer-counter"
            aria-invalid={over || undefined}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={onKeyDown}
          />
          <SendOrStop streaming={streaming} canSend={canSend} onStop={onStop} />
        </div>
        <div className="composer-meta">
          <span id="composer-hint">{reason ?? vi.chat.hint}</span>
          {followUpAvailable && (
            <label className="xs">
              <input type="checkbox" checked={followUp} onChange={(e) => setFollowUp(e.target.checked)} />{" "}
              {vi.chat.followUp}
            </label>
          )}
          <Counter count={count} />
        </div>
      </form>
    </div>
  );
});
