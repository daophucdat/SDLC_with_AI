import { render } from "@testing-library/react";
import axe from "axe-core";
import type { ReactElement } from "react";
import { MemoryRouter } from "react-router-dom";
import { App, makeQueryClient } from "../App";
import type { DocumentDto, MeDto } from "../api-client/types";

export const ME: MeDto = {
  id: "u-1",
  displayName: "Trần Thu Hà",
  email: "thu.ha@congty.vn",
  role: "BD_MEMBER",
  permissions: [],
  flags: [],
};

export function doc(p: Partial<DocumentDto> = {}): DocumentDto {
  return {
    id: "d-1",
    fileName: "Hop-dong-ABC.pdf",
    pageCount: 12,
    status: "READY",
    errorCode: null,
    uploadedBy: { id: "u-1", displayName: "Trần Thu Hà" },
    uploadedAt: "2026-10-20T08:00:00Z",
    canRemove: true,
    ...p,
  };
}

/** Byte stream that yields the given chunks, then (optionally) fails like a dropped connection. */
export function chunkedBody(chunks: string[], opts: { failAtEnd?: boolean } = {}) {
  const enc = new TextEncoder();
  let i = 0;
  return {
    getReader: () => ({
      read: async () => {
        if (i < chunks.length) return { done: false, value: enc.encode(chunks[i++]) };
        if (opts.failAtEnd) throw new TypeError("network error");
        return { done: true, value: undefined };
      },
      cancel: async () => undefined,
    }),
  };
}

/** Minimal Response stand-in: Node 16 (local dev) has no global Response; CI runs Node 20. */
export function fakeResponse(status: number, text: string, body?: ReturnType<typeof chunkedBody>) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => JSON.parse(text),
    text: async () => text,
    body: body ?? null,
  } as unknown as Response;
}

export function sseEvent(event: string, data: unknown): string {
  return `event: ${event}
data: ${JSON.stringify(data)}

`;
}

type Reply = { status: number; body?: unknown; sse?: string[]; failAtEnd?: boolean };
type Handler = (url: string, init: RequestInit) => Reply | undefined;

/** Routes fetch() to a handler; returns the recorded calls. Unhandled URLs answer 404 NOT_FOUND. */
export function mockFetch(handler: Handler) {
  const calls: { url: string; init: RequestInit }[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init: RequestInit = {}) => {
      calls.push({ url, init });
      const r = handler(url, init) ?? { status: 404, body: { code: "NOT_FOUND" } };
      if (r.sse) return fakeResponse(r.status, "", chunkedBody(r.sse, { failAtEnd: r.failAtEnd }));
      return fakeResponse(r.status, r.body === undefined ? "" : JSON.stringify(r.body));
    }),
  );
  return calls;
}

export function renderApp(path = "/") {
  const client = makeQueryClient();
  client.setDefaultOptions({ queries: { ...client.getDefaultOptions().queries, retry: false } });
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App client={client} />
    </MemoryRouter>,
  );
}

export function renderInRouter(ui: ReactElement) {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
}

/** axe without colour-contrast: jsdom computes no CSS. */
export async function axeViolations(node: Element) {
  const res = await axe.run(node, { rules: { "color-contrast": { enabled: false } } });
  return res.violations.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(" ")).join(", ")}`);
}
