// useAsk (T301.4, T306.2, T306.3, T310.3): sends a question, feeds SSE events into the chat store, batches deltas per
// animation frame so the card does not re-render for every character, and stops / aborts cleanly.
import { useCallback, useEffect, useRef } from "react";
import { ApiError } from "../api-client/http";
import { askQuestion, createConversation, stopAnswer } from "../api-client/qa";
import type { CitationDto, NotFoundReason } from "../api-client/types";
import { newTurnKey, useChatStore } from "../state/chatStore";

const frame: (cb: () => void) => void =
  typeof requestAnimationFrame === "function" ? (cb) => requestAnimationFrame(cb) : (cb) => setTimeout(cb, 16);

export interface AskOptions {
  isSuggested?: boolean;
  followUp?: boolean;
}

export function useAsk(onAnnounce: (message: string) => void) {
  const controllers = useRef(new Set<AbortController>());

  useEffect(() => {
    const set = controllers.current;
    return () => set.forEach((c) => c.abort()); // leaving the page cancels the request (T301.4)
  }, []);

  const ensureConversation = useCallback(async (): Promise<string> => {
    const { conversationId, setConversation } = useChatStore.getState();
    if (conversationId) return conversationId;
    const { id } = await createConversation();
    setConversation(id);
    return id;
  }, []);

  const ask = useCallback(
    async (question: string, opts: AskOptions = {}) => {
      const store = useChatStore.getState();
      const key = newTurnKey();
      store.addTurn({ key, question, isSuggested: !!opts.isSuggested, state: "SEARCHING", text: "", citations: [] });
      const dispatch = useChatStore.getState().dispatch;
      const controller = new AbortController();
      controllers.current.add(controller);

      let pending = "";
      let scheduled = false;
      const flush = () => {
        scheduled = false;
        if (pending) {
          dispatch(key, { type: "delta", text: pending });
          pending = "";
        }
      };

      const send = async (conversationId: string) =>
        askQuestion(
          conversationId,
          { text: question, followUp: !!opts.followUp, isSuggested: !!opts.isSuggested },
          controller.signal,
        );

      try {
        let conv = await ensureConversation();
        let stream;
        try {
          stream = await send(conv);
        } catch (e) {
          // The session's conversation is gone (logout elsewhere, server restart of a dev DB): start a new one.
          if (!(e instanceof ApiError && e.code === "NOT_FOUND")) throw e;
          useChatStore.getState().setConversation(null);
          conv = await ensureConversation();
          stream = await send(conv);
        }
        let started = false;
        for await (const ev of stream) {
          const data = ev.data as Record<string, unknown>;
          if (ev.event === "delta") {
            if (!started) {
              started = true;
              onAnnounce("Đang soạn câu trả lời");
            }
            pending += String(data.text ?? "");
            if (!scheduled) {
              scheduled = true;
              frame(flush);
            }
            continue;
          }
          flush();
          if (ev.event === "meta") {
            dispatch(key, {
              type: "meta",
              questionId: String(data.questionId),
              answerId: String(data.answerId),
              readyDocCount: Number(data.readyDocCount ?? 0),
              processingDocCount: Number(data.processingDocCount ?? 0),
            });
          } else if (ev.event === "citations") {
            dispatch(key, {
              type: "citations",
              text: String(data.text ?? ""),
              items: (data.items ?? []) as CitationDto[],
            });
          } else if (ev.event === "done") {
            const status = data.status as "COMPLETED" | "NOT_FOUND" | "STOPPED";
            dispatch(key, { type: "done", status, reason: (data.reason ?? null) as NotFoundReason | null });
            onAnnounce(
              status === "COMPLETED" ? "Đã trả lời xong" : status === "NOT_FOUND" ? "Không tìm thấy" : "Đã dừng",
            );
          } else if (ev.event === "error") {
            dispatch(key, { type: "error", code: String(data.code ?? "INTERNAL") });
            onAnnounce("Chưa trả lời được");
          }
        }
        flush();
        dispatch(key, { type: "closed" }); // no-op when a final event arrived (§0.5 rule 1)
      } catch (e) {
        flush();
        if ((e as Error)?.name === "AbortError") {
          dispatch(key, { type: "closed" });
        } else if (e instanceof ApiError && e.status > 0) {
          dispatch(key, { type: "error", code: e.code });
        } else {
          dispatch(key, { type: "closed" }); // network loss mid-stream → INCOMPLETE (EC-05)
        }
      } finally {
        controllers.current.delete(controller);
      }
    },
    [ensureConversation, onAnnounce],
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
