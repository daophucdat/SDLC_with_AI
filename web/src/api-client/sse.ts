// SSE over fetch (T301.4). EventSource cannot POST or send the CSRF header, so the stream is read by hand:
// events are separated by a blank line, comment lines (": ping") are ignored (dev_tasks.md §0.5).
import { ApiError, authRequired, csrfToken, CSRF_HEADER, problemOf } from "./http";

export interface SseEvent {
  event: string;
  data: unknown;
}

function splitField(line: string): [string, string] {
  const i = line.indexOf(":");
  return i < 0 ? [line, ""] : [line.slice(0, i), line.slice(i + 1).replace(/^ /, "")];
}

/** One event block → event, or null for comment-only / malformed blocks (the stream continues). */
function parseBlock(block: string): SseEvent | null {
  let event = "message";
  const data: string[] = [];
  for (const line of block.split("\n")) {
    if (!line || line.startsWith(":")) continue;
    const [field, value] = splitField(line);
    if (field === "event") event = value;
    else if (field === "data") data.push(value);
  }
  if (!data.length) return null;
  try {
    return { event, data: JSON.parse(data.join("\n")) };
  } catch {
    return null;
  }
}

/** Parses complete events out of `buffer`; returns them and the unfinished tail. */
export function parseSse(buffer: string): { events: SseEvent[]; rest: string } {
  const blocks = buffer.replace(/\r\n/g, "\n").split("\n\n");
  const rest = blocks.pop() ?? "";
  const events = blocks.map(parseBlock).filter((e): e is SseEvent => e !== null);
  return { events, rest };
}

interface ByteReader {
  read(): Promise<{ done: boolean; value?: Uint8Array }>;
  cancel(): Promise<void>;
}

export async function* readSse(body: { getReader(): ByteReader }): AsyncGenerator<SseEvent> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const { events, rest } = parseSse(buffer);
      buffer = rest;
      for (const e of events) yield e;
    }
    const { events } = parseSse(buffer + decoder.decode() + "\n\n");
    for (const e of events) yield e;
  } finally {
    reader.cancel().catch(() => undefined);
  }
}

/** POSTs JSON and returns the event stream. Errors before the stream opens are thrown as ApiError. */
export async function postSse(path: string, body: unknown, signal?: AbortSignal): Promise<AsyncGenerator<SseEvent>> {
  const headers = new Headers({ "Content-Type": "application/json", Accept: "text/event-stream" });
  const token = csrfToken();
  if (token) headers.set(CSRF_HEADER, token);
  let res: Response;
  try {
    res = await fetch(path, {
      method: "POST",
      headers,
      body: JSON.stringify(body),
      credentials: "same-origin",
      signal,
    });
  } catch (e) {
    if ((e as Error)?.name === "AbortError") throw e;
    throw new ApiError({ status: 0, code: "NETWORK" });
  }
  if (!res.ok) {
    const problem = problemOf(res.status, await res.json().catch(() => null));
    if (problem.code === "AUTH_REQUIRED") authRequired();
    throw new ApiError(problem);
  }
  if (!res.body) throw new ApiError({ status: res.status, code: "INTERNAL" });
  return readSse(res.body as unknown as { getReader(): ByteReader });
}
