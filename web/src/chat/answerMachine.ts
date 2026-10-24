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

export function answerReducer(turn: ChatTurn, action: AnswerAction): ChatTurn {
  if (FINAL.has(turn.state)) return turn; // a final state never changes
  switch (action.type) {
    case "meta":
      return {
        ...turn,
        questionId: action.questionId,
        answerId: action.answerId,
        readyDocCount: action.readyDocCount,
        processingDocCount: action.processingDocCount,
      };
    case "delta":
      // after "Dừng" the UI stops showing new text immediately (AC-310.1), even before `done STOPPED` arrives
      if (turn.stopRequested) return turn;
      return { ...turn, state: "STREAMING", text: turn.text + action.text };
    case "citations":
      // The final text is renumbered on the server (DQ-01): replace what was streamed.
      return { ...turn, text: action.text, citations: action.items };
    case "done":
      if (action.status === "NOT_FOUND") {
        return { ...turn, state: "NOT_FOUND", reason: action.reason ?? null, replaced: turn.text.length > 0, text: "" };
      }
      return { ...turn, state: action.status };
    case "error":
      return { ...turn, state: "FAILED", errorCode: action.code };
    case "stopRequested":
      return { ...turn, stopRequested: true };
    case "closed":
      if (turn.stopRequested) return { ...turn, state: "STOPPED" };
      return { ...turn, state: turn.text ? "INCOMPLETE" : "FAILED", errorCode: turn.text ? undefined : "NETWORK" };
  }
}

/** Indices actually cited in the text, in order (the source list shows these). */
export function citedIndices(text: string): number[] {
  return [...new Set([...text.matchAll(/\[(\d+)\]/g)].map((m) => Number(m[1])))];
}
