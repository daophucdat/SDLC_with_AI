// AnswerCard state machine (T306.1, Blueprint §3.7) as a pure reducer:
// SEARCHING → STREAMING → COMPLETED | NOT_FOUND | STOPPED | FAILED | INCOMPLETE
import type { CitationDto, NotFoundReason } from "../api-client/types";

export type AnswerState = "SEARCHING" | "STREAMING" | "COMPLETED" | "NOT_FOUND" | "STOPPED" | "FAILED" | "INCOMPLETE";

export interface ChatTurn {
  key: string;
  question: string;
  isSuggested: boolean;
  questionId?: string;
  answerId?: string;
  state: AnswerState;
  text: string;
  citations: CitationDto[];
  readyDocCount?: number;
  processingDocCount?: number;
  reason?: NotFoundReason | null;
  errorCode?: string;
  replaced?: boolean; // NOT_FOUND after text was already shown (EC-14)
  stopRequested?: boolean;
  feedback?: "HELPFUL" | "NOT_HELPFUL" | null;
}

export type AnswerAction =
  | { type: "meta"; questionId: string; answerId: string; readyDocCount: number; processingDocCount: number }
  | { type: "delta"; text: string }
  | { type: "citations"; text: string; items: CitationDto[] }
  | { type: "done"; status: "COMPLETED" | "NOT_FOUND" | "STOPPED"; reason?: NotFoundReason | null }
  | { type: "error"; code: string }
  | { type: "stopRequested" }
  | { type: "closed" }; // stream ended (or broke) — only matters if no final event arrived

export const FINAL: ReadonlySet<AnswerState> = new Set(["COMPLETED", "NOT_FOUND", "STOPPED", "FAILED", "INCOMPLETE"]);

type Handler<T extends AnswerAction["type"]> = (turn: ChatTurn, action: Extract<AnswerAction, { type: T }>) => ChatTurn;

const HANDLERS: { [T in AnswerAction["type"]]: Handler<T> } = {
  meta: (turn, a) => ({
    ...turn,
    questionId: a.questionId,
    answerId: a.answerId,
    readyDocCount: a.readyDocCount,
    processingDocCount: a.processingDocCount,
  }),
  // after "Dừng" the UI stops showing new text immediately (AC-310.1), even before `done STOPPED` arrives
  delta: (turn, a) => (turn.stopRequested ? turn : { ...turn, state: "STREAMING", text: turn.text + a.text }),
  // the final text is renumbered on the server (DQ-01): replace what was streamed
  citations: (turn, a) => ({ ...turn, text: a.text, citations: a.items }),
  done: (turn, a) =>
    a.status === "NOT_FOUND"
      ? { ...turn, state: "NOT_FOUND", reason: a.reason ?? null, replaced: turn.text.length > 0, text: "" }
      : { ...turn, state: a.status },
  error: (turn, a) => ({ ...turn, state: "FAILED", errorCode: a.code }),
  stopRequested: (turn) => ({ ...turn, stopRequested: true }),
  closed: (turn) => {
    if (turn.stopRequested) return { ...turn, state: "STOPPED" };
    return turn.text ? { ...turn, state: "INCOMPLETE" } : { ...turn, state: "FAILED", errorCode: "NETWORK" };
  },
};

export function answerReducer(turn: ChatTurn, action: AnswerAction): ChatTurn {
  if (FINAL.has(turn.state)) return turn; // a final state never changes
  return (HANDLERS[action.type] as Handler<typeof action.type>)(turn, action as never);
}

/** Indices actually cited in the text, in order (the source list shows these). */
export function citedIndices(text: string): number[] {
  return [...new Set([...text.matchAll(/\[(\d+)\]/g)].map((m) => Number(m[1])))];
}
