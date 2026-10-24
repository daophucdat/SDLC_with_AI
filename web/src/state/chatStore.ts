// useChatStore (dev_tasks.md §0.9): the current conversation of this session (PD-04) and its turns.
import { create } from "zustand";
import type { TurnDto } from "../api-client/types";
import { answerReducer } from "../chat/answerMachine";
import type { AnswerAction, ChatTurn } from "../chat/answerMachine";

const CONV_KEY = "chat.conversationId";

function readConv(): string | null {
  try {
    return sessionStorage.getItem(CONV_KEY);
  } catch {
    return null;
  }
}

function writeConv(id: string | null): void {
  try {
    if (id) sessionStorage.setItem(CONV_KEY, id);
    else sessionStorage.removeItem(CONV_KEY);
  } catch {
    /* storage unavailable: the conversation simply is not restored after reload */
  }
}

export interface SourceRef {
  turnKey: string;
  index: number;
  documentId: string;
  fileName: string;
  page: number;
  excerpt: string;
}

interface ChatState {
  conversationId: string | null;
  turns: ChatTurn[];
  removedDocIds: Set<string>;
  source: SourceRef | null;
  setConversation: (id: string | null) => void;
  addTurn: (turn: ChatTurn) => void;
  dispatch: (key: string, action: AnswerAction) => void;
  patchTurn: (key: string, patch: Partial<ChatTurn>) => void;
  removeTurn: (key: string) => void;
  restore: (turns: TurnDto[]) => void;
  markRemoved: (documentIds: string[]) => void;
  openSource: (ref: SourceRef | null) => void;
  reset: () => void;
}

let seq = 0;
export const newTurnKey = () => `t${Date.now().toString(36)}${++seq}`;

export const useChatStore = create<ChatState>((set) => ({
  conversationId: readConv(),
  turns: [],
  removedDocIds: new Set(),
  source: null,
  setConversation: (id) => {
    writeConv(id);
    set({ conversationId: id });
  },
  addTurn: (turn) => set((s) => ({ turns: [...s.turns, turn] })),
  dispatch: (key, action) =>
    set((s) => ({ turns: s.turns.map((t) => (t.key === key ? answerReducer(t, action) : t)) })),
  patchTurn: (key, patch) => set((s) => ({ turns: s.turns.map((t) => (t.key === key ? { ...t, ...patch } : t)) })),
  removeTurn: (key) => set((s) => ({ turns: s.turns.filter((t) => t.key !== key) })),
  restore: (dtos) =>
    set({
      turns: dtos.map((d) => ({
        key: newTurnKey(),
        question: d.text,
        isSuggested: false,
        questionId: d.questionId,
        answerId: d.answer.answerId,
        // an answer still STREAMING on the server after a reload is shown as incomplete
        state: d.answer.status === "STREAMING" ? "INCOMPLETE" : d.answer.status,
        text: d.answer.text,
        citations: d.answer.citations,
        feedback: d.answer.feedback ?? null,
      })),
    }),
  markRemoved: (ids) =>
    set((s) => {
      if (ids.every((id) => s.removedDocIds.has(id))) return s;
      const next = new Set(s.removedDocIds);
      ids.forEach((id) => next.add(id));
      return { removedDocIds: next };
    }),
  openSource: (ref) => set({ source: ref }),
  reset: () => {
    writeConv(null);
    set({ conversationId: null, turns: [], source: null, removedDocIds: new Set() });
  },
}));

export const isRemoved = (c: { documentId: string; removed: boolean }, removed: Set<string>) =>
  c.removed || removed.has(c.documentId);
