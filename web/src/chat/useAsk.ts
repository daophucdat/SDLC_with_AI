// useAsk (T301.4, T306.2, T306.3, T310.3): sends a question, feeds SSE events into the chat store, batches deltas per
// animation frame so the card does not re-render for every character, and stops / aborts cleanly.
import { useCallback, useEffect, useRef } from "react";
import { ApiError } from "../api-client/http";
import { askQuestion, createConversation, stopAnswer } from "../api-client/qa";
import type { SseEvent } from "../api-client/sse";
import type { CitationDto, NotFoundReason } from "../api-client/types";
import { newTurnKey, useChatStore } from "../state/chatStore";
import type { AnswerAction } from "./answerMachine";

const frame: (cb: () => void) => void =
  typeof requestAnimationFrame === "function" ? (cb) => requestAnimationFrame(cb) : (cb) => setTimeout(cb, 16);

export interface AskOptions {
  isSuggested?: boolean;
  followUp?: boolean;
}

/** Collects delta text and hands it over at most once per animation frame (T306.2). */
class DeltaBatcher {
  private pending = "";
  private scheduled = false;

  constructor(private readonly emit: (text: string) => void) {}

  add(text: string): void {
    this.pending += text;
    if (this.scheduled) return;
    this.scheduled = true;
    frame(() => this.flush());
  }

  flush(): void {
    this.scheduled = false;
    if (!this.pending) return;
    this.emit(this.pending);
    this.pending = "";
  }
}

type Data = Record<string, unknown>;

const str = (v: unknown, fallback = "") => (v == null ? fallback : String(v));
const num = (v: unknown) => Number(v ?? 0);

const BUILDERS: Record<string, (d: Data) => AnswerAction> = {
  meta: (d) => ({
    type: "meta",
    questionId: str(d.questionId),
    answerId: str(d.answerId),
    readyDocCount: num(d.readyDocCount),
    processingDocCount: num(d.processingDocCount),
  }),
  citations: (d) => ({ type: "citations", text: str(d.text), items: (d.items ?? []) as CitationDto[] }),
  done: (d) => ({
    type: "done",
    status: d.status as "COMPLETED" | "NOT_FOUND" | "STOPPED",
    reason: (d.reason ?? null) as NotFoundReason | null,
  }),
  error: (d) => ({ type: "error", code: str(d.code, "INTERNAL") }),
};

/** SSE event (§0.5) → reducer action; deltas are batched separately, unknown events ignored. */
export function toAction(ev: SseEvent): AnswerAction | null {
  const build = BUILDERS[ev.event];
  return build ? build(ev.data as Data) : null;
}

const DONE_ANNOUNCEMENT: Record<string, string> = {
  COMPLETED: "Đã trả lời xong",
  NOT_FOUND: "Không tìm thấy",
  STOPPED: "Đã dừng",
};

function announcementFor(action: AnswerAction): string | null {
  if (action.type === "done") return DONE_ANNOUNCEMENT[action.status];
  if (action.type === "error") return "Chưa trả lời được";
  return null;
}

/** A request that failed before or during the stream → the reducer action that describes it. */
function failureAction(e: unknown): AnswerAction {
  if (e instanceof ApiError && e.status > 0) return { type: "error", code: e.code };
  return { type: "closed" }; // aborted, or network loss mid-stream → INCOMPLETE (EC-05)
}

async function ensureConversation(): Promise<string> {
  const { conversationId, setConversation } = useChatStore.getState();
  if (conversationId) return conversationId;
  const { id } = await createConversation();
  setConversation(id);
  return id;
}

/** Opens the answer stream; if the session's conversation is gone (logout elsewhere, dev DB reset), starts a new one. */
async function openStream(question: string, opts: AskOptions, signal: AbortSignal) {
  const body = { text: question, followUp: !!opts.followUp, isSuggested: !!opts.isSuggested };
  try {
    return await askQuestion(await ensureConversation(), body, signal);
  } catch (e) {
    if (!(e instanceof ApiError && e.code === "NOT_FOUND")) throw e;
    useChatStore.getState().setConversation(null);
    return askQuestion(await ensureConversation(), body, signal);
  }
}

export function useAsk(onAnnounce: (message: string) => void) {
  const controllers = useRef(new Set<AbortController>());

  useEffect(() => {
    const set = controllers.current;
    return () => set.forEach((c) => c.abort()); // leaving the page cancels the request (T301.4)
  }, []);

  const ask = useCallback(
    async (question: string, opts: AskOptions = {}) => {
      const key = newTurnKey();
      const { addTurn, dispatch } = useChatStore.getState();
      addTurn({ key, question, isSuggested: !!opts.isSuggested, state: "SEARCHING", text: "", citations: [] });
      const controller = new AbortController();
      controllers.current.add(controller);
      const deltas = new DeltaBatcher((text) => dispatch(key, { type: "delta", text }));
      let started = false;
      try {
        for await (const ev of await openStream(question, opts, controller.signal)) {
          if (ev.event === "delta") {
            if (!started) onAnnounce("Đang soạn câu trả lời");
            started = true;
            deltas.add(String((ev.data as Data).text ?? ""));
            continue;
          }
          deltas.flush();
          const action = toAction(ev);
          if (!action) continue;
          dispatch(key, action);
          const message = announcementFor(action);
          if (message) onAnnounce(message);
        }
        deltas.flush();
        dispatch(key, { type: "closed" }); // no-op when a final event arrived (§0.5 rule 1)
      } catch (e) {
        deltas.flush();
        dispatch(key, failureAction(e));
      } finally {
        controllers.current.delete(controller);
      }
    },
    [onAnnounce],
  );

  const stop = useCallback(async (key: string) => {
    const turn = useChatStore.getState().turns.find((t) => t.key === key);
    if (!turn) return;
    useChatStore.getState().dispatch(key, { type: "stopRequested" }); // stop showing text now (≤ 1 s, AC-310.1)
    if (turn.answerId) {
      await stopAnswer(turn.answerId).catch(() => undefined); // 409 if it finished meanwhile: nothing to do
    }
  }, []);

  return { ask, stop };
}
