import { parseSse, readSse } from "../api-client/sse";
import { findExcerpt } from "../source-viewer/pdf";
import { chunkedBody, sseEvent } from "../test/utils";
import { answerReducer, citedIndices } from "./answerMachine";
import type { AnswerAction, ChatTurn } from "./answerMachine";

const base: ChatTurn = { key: "t1", question: "Q?", isSuggested: false, state: "SEARCHING", text: "", citations: [] };
const cite = { index: 1, documentId: "d1", fileName: "a.pdf", page: 3, excerpt: "x", removed: false };
const run = (actions: AnswerAction[], from = base) => actions.reduce(answerReducer, from);

describe("SSE parsing (T301.4)", () => {
  it("splits events, skips pings and keeps the unfinished tail", () => {
    const { events, rest } = parseSse(': ping\n\nevent: delta\ndata: {"text":"Xin"}\n\nevent: done\ndata: {"st');
    expect(events).toEqual([{ event: "delta", data: { text: "Xin" } }]);
    expect(rest).toBe('event: done\ndata: {"st');
  });

  it("handles CRLF and multi-line data", () => {
    const { events } = parseSse('event: meta\r\ndata: {"a":\r\ndata: 1}\r\n\r\n');
    expect(events).toEqual([{ event: "meta", data: { a: 1 } }]);
  });

  it("reassembles events split across chunks, including multi-byte characters", async () => {
    const whole = sseEvent("delta", { text: "Thanh toán 30% [1]" }) + sseEvent("done", { status: "COMPLETED" });
    const chunks = [whole.slice(0, 17), whole.slice(17, 40), whole.slice(40)];
    const out = [];
    for await (const e of readSse(chunkedBody(chunks))) out.push(e);
    expect(out.map((e) => e.event)).toEqual(["delta", "done"]);
    expect((out[0].data as { text: string }).text).toBe("Thanh toán 30% [1]");
  });
});

describe("answer state machine (T306.1)", () => {
  const meta: AnswerAction = { type: "meta", questionId: "q", answerId: "a", readyDocCount: 3, processingDocCount: 1 };

  it("SEARCHING → STREAMING → COMPLETED, citations replace the streamed text (DQ-01)", () => {
    const t = run([
      meta,
      { type: "delta", text: "Ý chính [3]" },
      { type: "citations", text: "Ý chính [1]", items: [cite] },
      { type: "done", status: "COMPLETED" },
    ]);
    expect(t).toMatchObject({ state: "COMPLETED", text: "Ý chính [1]", answerId: "a", processingDocCount: 1 });
  });

  it("short answers without deltas still complete", () => {
    expect(
      run([meta, { type: "citations", text: "Có [1].", items: [cite] }, { type: "done", status: "COMPLETED" }]),
    ).toMatchObject({ state: "COMPLETED", text: "Có [1]." });
  });

  it("NOT_FOUND after deltas replaces the text and says so (EC-14)", () => {
    const t = run([
      meta,
      { type: "delta", text: "Theo tài liệu" },
      { type: "done", status: "NOT_FOUND", reason: "INVALID_CITATIONS" },
    ]);
    expect(t).toMatchObject({ state: "NOT_FOUND", text: "", replaced: true, reason: "INVALID_CITATIONS" });
    expect(run([meta, { type: "done", status: "NOT_FOUND", reason: "NO_CHUNKS" }]).replaced).toBe(false);
  });

  it("error → FAILED with the code", () => {
    expect(run([meta, { type: "error", code: "AI_TIMEOUT" }])).toMatchObject({
      state: "FAILED",
      errorCode: "AI_TIMEOUT",
    });
  });

  it("stream closed without a final event → INCOMPLETE (keeps text) or FAILED (nothing received) (EC-05)", () => {
    expect(run([meta, { type: "delta", text: "Một phần" }, { type: "closed" }])).toMatchObject({
      state: "INCOMPLETE",
      text: "Một phần",
    });
    expect(run([meta, { type: "closed" }])).toMatchObject({ state: "FAILED", errorCode: "NETWORK" });
  });

  it("stop: no more text is shown, then STOPPED (AC-310.1)", () => {
    const t = run([meta, { type: "delta", text: "Một " }, { type: "stopRequested" }, { type: "delta", text: "hai" }]);
    expect(t.text).toBe("Một ");
    expect(answerReducer(t, { type: "done", status: "STOPPED" }).state).toBe("STOPPED");
    expect(answerReducer(t, { type: "closed" }).state).toBe("STOPPED");
  });

  it("final states never change", () => {
    const done = run([meta, { type: "done", status: "COMPLETED" }]);
    expect(run([{ type: "delta", text: "x" }, { type: "error", code: "INTERNAL" }, { type: "closed" }], done)).toBe(
      done,
    );
  });

  it("cited indices in order of appearance", () => {
    expect(citedIndices("a [2] b [1][2] c [3]")).toEqual([2, 1, 3]);
  });
});

describe("excerpt highlight (T305.3)", () => {
  it("finds the excerpt across text-layer items, ignoring case, spacing and Unicode form", () => {
    const items = ["Điều 5.", "Thanh toán:", "khách hàng thanh", "toán 30% khi ký", "hợp đồng.", "Điều 6."];
    const excerpt = "Thanh toán: khách hàng THANH   toán 30% khi ký hợp đồng.".normalize("NFD");
    expect(findExcerpt(items, excerpt)).toEqual([1, 2, 3, 4]);
  });

  it("returns nothing when not on the page or too short", () => {
    expect(findExcerpt(["abc def"], "không có ở đây")).toEqual([]);
    expect(findExcerpt(["abc"], "abc")).toEqual([]);
  });
});
