// Workspace (F1 → F4): AppShell + LibraryPanel + chat + source panel, global banners (offline EC-06, AI outage REL-04,
// session expired EC-17 / US-103) and conversation restore after reload (US-308, flag "history").
import { lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api, loginUrl, nav, setAuthRequiredHandler } from "../api-client/http";
import { getHistory } from "../api-client/qa";
import { useMe } from "../auth/RequireAuth";
import { ChatThread } from "../chat/ChatThread";
import { QuestionComposer } from "../chat/QuestionComposer";
import type { ComposerHandle } from "../chat/QuestionComposer";
import type { ChatTurn } from "../chat/answerMachine";
import { useAsk } from "../chat/useAsk";
import { LibraryPanel } from "../features/library/LibraryPanel";
import { useDocuments } from "../features/library/useDocuments";
import { fmt, vi } from "../i18n/vi";
import { useChatStore } from "../state/chatStore";
import type { SourceRef } from "../state/chatStore";
import { useUiStore } from "../state/uiStore";
import { AppShell, Button, GlobalBanner, Spinner, useToast } from "../ui";

const SourcePanel = lazy(() => import("../source-viewer/SourcePanel"));

function useOnline(): boolean {
  const [online, setOnline] = useState(() => navigator.onLine);
  useEffect(() => {
    const on = () => setOnline(true);
    const off = () => setOnline(false);
    window.addEventListener("online", on);
    window.addEventListener("offline", off);
    return () => {
      window.removeEventListener("online", on);
      window.removeEventListener("offline", off);
    };
  }, []);
  return online;
}

/** US-103: a 401 inside the workspace shows a banner instead of navigating away (the draft stays in the composer). */
function useSessionExpiry(setSessionExpired: (v: boolean) => void): void {
  useEffect(() => {
    setAuthRequiredHandler(() => setSessionExpired(true));
    return () => setAuthRequiredHandler(null);
  }, [setSessionExpired]);
}

/** US-308: restore the session's conversation after a reload. */
function useHistoryRestore(enabled: boolean): void {
  useEffect(() => {
    const { conversationId, turns, restore, setConversation } = useChatStore.getState();
    if (!enabled || !conversationId || turns.length) return;
    getHistory(conversationId)
      .then(restore)
      .catch(() => setConversation(null));
  }, [enabled]);
}

/** T305.4: #src=<docId>:<page> deep link. */
function useSourceDeepLink(): void {
  useEffect(() => {
    const m = /^#src=([0-9a-f-]{36}):(\d+)$/i.exec(window.location.hash);
    if (!m || useChatStore.getState().source) return;
    const ref: SourceRef = { turnKey: "", index: 0, documentId: m[1], fileName: "", page: Number(m[2]), excerpt: "" };
    useChatStore.getState().openSource(ref);
  }, []);
}

/** REL-04: the outage banner appears after an AI_UNAVAILABLE answer and goes away with the next good one. */
function useAiAvailability(turns: ChatTurn[], setAiAvailable: (v: boolean) => void): void {
  useEffect(() => {
    const last = turns[turns.length - 1];
    if (last?.state === "FAILED" && last.errorCode === "AI_UNAVAILABLE") setAiAvailable(false);
    if (last?.state === "COMPLETED" || last?.state === "NOT_FOUND") setAiAvailable(true);
  }, [turns, setAiAvailable]);
}

/** Why the question box is disabled, in priority order (AC-301.5, EC-06, EC-17, REL-03), or null. */
export function composerDisabledReason(s: {
  sessionExpired: boolean;
  qaOff: boolean;
  online: boolean;
  readyCount: number;
  docsPending: boolean;
}): string | null {
  if (s.sessionExpired) return vi.banners.session;
  if (s.qaOff) return vi.chat.disabledAi;
  if (!s.online) return vi.chat.disabledOffline;
  if (!s.readyCount && !s.docsPending) return vi.chat.disabledNoDocs;
  return null;
}

function WorkspaceBanners(p: { sessionExpired: boolean; online: boolean; qaOff: boolean; aiAvailable: boolean }) {
  const setAiAvailable = useUiStore((s) => s.setAiAvailable);
  return (
    <>
      {p.sessionExpired && (
        <GlobalBanner
          tone="info"
          action={
            <Button variant="primary" onClick={() => nav.assign(loginUrl())}>
              {vi.banners.relogin}
            </Button>
          }
        >
          {vi.banners.session}
        </GlobalBanner>
      )}
      {!p.online && <GlobalBanner tone="warning">{vi.banners.offline}</GlobalBanner>}
      {p.qaOff && <GlobalBanner tone="warning">{vi.banners.ai}</GlobalBanner>}
      {!p.aiAvailable && !p.qaOff && (
        <GlobalBanner
          tone="warning"
          action={
            <Button variant="secondary" onClick={() => setAiAvailable(true)}>
              {vi.chat.retry}
            </Button>
          }
        >
          {vi.banners.ai}
        </GlobalBanner>
      )}
    </>
  );
}

function SourceSlot({ source }: { source: SourceRef }) {
  return (
    <Suspense
      fallback={
        <aside className="source-panel" aria-label={vi.source.label}>
          <div className="source-status">
            <Spinner label={vi.source.loading} />
          </div>
        </aside>
      }
    >
      <SourcePanel source={source} />
    </Suspense>
  );
}

async function logout() {
  await api("/auth/logout", { method: "POST" }).catch(() => undefined);
  useChatStore.getState().reset();
  window.location.assign("/login");
}

export function WorkspacePage() {
  const me = useMe();
  const toast = useToast();
  const online = useOnline();
  const flags = useMemo(() => new Set(me.flags), [me.flags]);
  const [libraryOpen, setLibraryOpen] = useState(false);
  const [announcement, setAnnouncement] = useState("");
  const composer = useRef<ComposerHandle>(null);

  const turns = useChatStore((s) => s.turns);
  const source = useChatStore((s) => s.source);
  const markRemoved = useChatStore((s) => s.markRemoved);
  const { aiAvailable, setAiAvailable, sessionExpired, setSessionExpired } = useUiStore();

  // Unfiltered list: drives counts, toasts and "removed" marks for citations.
  const docs = useDocuments("", {
    onReady: (d) => toast(fmt(vi.library.ready, { file: d.fileName }), "success"),
    onNoText: (d) => toast(fmt(vi.removeDoc.noTextToast, { file: d.fileName }), "info"),
    onGone: (ids) => markRemoved(ids),
  });
  const all = docs.data?.items ?? [];
  const readyCount = all.filter((d) => d.status === "READY").length;

  useSessionExpiry(setSessionExpired);
  useHistoryRestore(flags.has("history"));
  useSourceDeepLink();
  useAiAvailability(turns, setAiAvailable);

  const { ask, stop } = useAsk(setAnnouncement);
  const streamingTurn = turns.find((t) => t.state === "SEARCHING" || t.state === "STREAMING");
  const qaOff = flags.has("qa_off"); // REL-03 kill switch
  const disabledReason = composerDisabledReason({
    sessionExpired,
    qaOff,
    online,
    readyCount,
    docsPending: docs.isPending,
  });

  const submit = useCallback(
    (text: string, opts: { isSuggested?: boolean; followUp?: boolean } = {}) => {
      if (streamingTurn || disabledReason) return;
      ask(text, opts);
    },
    [ask, streamingTurn, disabledReason],
  );

  const askAgain = (turn: ChatTurn) => {
    useChatStore.getState().removeTurn(turn.key);
    submit(turn.question);
  };

  const stopStreaming = async () => {
    if (streamingTurn) await stop(streamingTurn.key);
    composer.current?.focus(); // T310.3
  };

  const last = turns[turns.length - 1];
  const followUpAvailable = flags.has("followup") && last?.state === "COMPLETED";

  return (
    <AppShell
      me={me}
      banners={
        <WorkspaceBanners sessionExpired={sessionExpired} online={online} qaOff={qaOff} aiAvailable={aiAvailable} />
      }
      library={<LibraryPanel meId={me.id} expanded={libraryOpen} />}
      libraryOpen={libraryOpen}
      onToggleLibrary={() => setLibraryOpen((o) => !o)}
      source={source && <SourceSlot source={source} />}
      onLogout={logout}
    >
      <ChatThread
        libraryEmpty={!docs.isPending && all.length === 0}
        readyDocCount={readyCount}
        canAsk={!disabledReason && !streamingTurn}
        streamRender={flags.has("stream_render")}
        announcement={announcement}
        onAsk={(q, o) => submit(q, o)}
        onRephrase={(q) => composer.current?.setText(q)}
        onAskAgain={askAgain}
      />
      <QuestionComposer
        ref={composer}
        disabledReason={disabledReason}
        streaming={!!streamingTurn}
        followUpAvailable={followUpAvailable}
        onSubmit={(text, followUp) => submit(text, { followUp })}
        onStop={stopStreaming}
      />
    </AppShell>
  );
}
