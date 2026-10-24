import { act, fireEvent, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { DocumentDto } from "../api-client/types";
import { useChatStore } from "../state/chatStore";
import { useUiStore } from "../state/uiStore";
import { axeViolations, doc, ME, mockFetch, renderApp, sseEvent } from "../test/utils";

vi.mock("../analytics/track", () => ({ track: vi.fn() }));
const pdfMock = vi.hoisted(() => ({ open: vi.fn() }));
vi.mock("../source-viewer/pdf", async (orig) => {
  const real = await orig<typeof import("../source-viewer/pdf")>();
  return { ...real, openPdf: pdfMock.open };
});

const CITES = [
  {
    index: 1,
    documentId: "d-1",
    fileName: "Hop-dong-ABC.pdf",
    page: 3,
    excerpt: "Thanh toán 30% khi ký",
    removed: false,
  },
  { index: 2, documentId: "d-2", fileName: "Bao-gia.pdf", page: 7, excerpt: "Bảo hành", removed: false },
];

function completedStream(answer = "Thanh toán 30% khi ký [1].\n\nBảo hành 24 tháng [2].") {
  return [
    sseEvent("meta", { questionId: "q1", answerId: "a1", readyDocCount: 2, processingDocCount: 1 }),
    sseEvent("delta", { text: answer.slice(0, 20) }),
    ": ping\n\n",
    sseEvent("delta", { text: answer.slice(20) }),
    sseEvent("citations", { text: answer, items: CITES }),
    sseEvent("done", { status: "COMPLETED", reason: null, latencyMs: 900 }),
  ];
}

type Reply = { status: number; body?: unknown; sse?: string[]; failAtEnd?: boolean } | undefined;

function serve(opts: { docs?: DocumentDto[]; ask?: (body: Record<string, unknown>) => Reply; me?: object } = {}) {
  const docs = opts.docs ?? [
    doc({ id: "d-1", fileName: "Hop-dong-ABC.pdf" }),
    doc({ id: "d-2", fileName: "Bao-gia.pdf" }),
  ];
  return mockFetch((url, init) => {
    if (url === "/api/v1/me") return { status: 200, body: { ...ME, ...opts.me } };
    if (url.startsWith("/api/v1/documents?")) return { status: 200, body: { items: docs, nextCursor: null } };
    if (url === "/api/v1/conversations") return { status: 201, body: { id: "c-1" } };
    if (url === "/api/v1/conversations/c-1/questions" && init.method === "POST")
      return (opts.ask ?? (() => ({ status: 200, sse: completedStream() })))(JSON.parse(String(init.body)));
    if (url === "/api/v1/answers/a1/feedback") return { status: 204 };
    if (url === "/api/v1/answers/a1/stop") return { status: 202 };
    if (url === "/api/v1/events") return { status: 202 };
  });
}

beforeEach(() => {
  sessionStorage.clear();
  useChatStore.getState().reset();
  useUiStore.setState({ aiAvailable: true, sessionExpired: false });
  pdfMock.open.mockReset();
});
afterEach(() => {
  vi.unstubAllGlobals();
});

async function askViaComposer(text: string) {
  const box = await screen.findByLabelText("Câu hỏi về tài liệu");
  await waitFor(() => expect(box).not.toBeDisabled());
  fireEvent.change(box, { target: { value: text } });
  fireEvent.keyDown(box, { key: "Enter" });
}

describe("US-301 → US-304 asking", () => {
  it("streams an answer with citation chips, a source list and the processing note (AC-301.1, AC-303.1)", async () => {
    const calls = serve();
    const { container } = renderApp("/");
    await askViaComposer("Điều khoản thanh toán?");
    const chip = await screen.findByRole("button", { name: "Nguồn 1: Hop-dong-ABC.pdf, trang 3" });
    expect(chip).toHaveClass("cite");
    expect(screen.getByRole("button", { name: "Mở Nguồn 2: Bao-gia.pdf, trang 7" })).toBeInTheDocument();
    expect(screen.getByText("1 tài liệu đang được xử lý, chưa được dùng cho câu trả lời này.")).toBeInTheDocument();
    const post = calls.find((c) => c.url.endsWith("/questions"))!;
    expect(JSON.parse(String(post.init.body))).toEqual({
      text: "Điều khoản thanh toán?",
      followUp: false,
      isSuggested: false,
    });
    expect(screen.getByLabelText("Câu hỏi về tài liệu")).toHaveValue("");
    expect(await axeViolations(container)).toEqual([]);
  });

  it("Enter on empty / whitespace sends nothing; Shift+Enter and IME composition do not send (AC-301.3)", async () => {
    const calls = serve();
    renderApp("/");
    const box = await screen.findByLabelText("Câu hỏi về tài liệu");
    await waitFor(() => expect(box).not.toBeDisabled());
    fireEvent.change(box, { target: { value: "   " } });
    fireEvent.keyDown(box, { key: "Enter" });
    fireEvent.change(box, { target: { value: "Giá" } });
    fireEvent.keyDown(box, { key: "Enter", shiftKey: true });
    fireEvent.keyDown(box, { key: "Enter", isComposing: true });
    fireEvent.keyDown(box, { key: "Enter", keyCode: 229 });
    expect(calls.some((c) => c.url.endsWith("/questions"))).toBe(false);
  });

  it("counter warns above 1,800 and blocks above 2,000 characters (AC-301.4)", async () => {
    serve();
    renderApp("/");
    const box = await screen.findByLabelText("Câu hỏi về tài liệu");
    await waitFor(() => expect(box).not.toBeDisabled());
    fireEvent.change(box, { target: { value: "a".repeat(1801) } });
    expect(screen.getByText("1801/2000")).toHaveClass("counter", "near");
    fireEvent.change(box, { target: { value: "a".repeat(2001) } });
    expect(screen.getByText("2001/2000")).toHaveClass("over");
    expect(screen.getByRole("button", { name: "Gửi" })).toBeDisabled();
    expect(screen.getByText("Câu hỏi vượt 2.000 ký tự.")).toBeInTheDocument();
  });

  it("composer is disabled with a reason when nothing is READY (AC-301.5)", async () => {
    serve({ docs: [doc({ id: "p", status: "PROCESSING" })] });
    renderApp("/");
    expect(await screen.findByText(/Chưa có tài liệu sẵn sàng/)).toBeInTheDocument();
    expect(screen.getByLabelText("Câu hỏi về tài liệu")).toBeDisabled();
  });

  it("empty library shows the big drop zone (EC-01); otherwise 3 suggestions marked is_suggested (EC-02)", async () => {
    serve({ docs: [] });
    const first = renderApp("/");
    expect(
      await screen.findByRole("heading", { name: "Tải tài liệu PDF đầu tiên để bắt đầu hỏi" }),
    ).toBeInTheDocument();
    first.unmount();

    const calls = serve();
    renderApp("/");
    const suggestion = await screen.findByRole("button", { name: "Thời hạn bảo hành trong hợp đồng X là bao lâu?" });
    await waitFor(() => expect(suggestion).not.toBeDisabled());
    fireEvent.click(suggestion);
    await screen.findByRole("button", { name: "Nguồn 1: Hop-dong-ABC.pdf, trang 3" });
    expect(JSON.parse(String(calls.find((c) => c.url.endsWith("/questions"))!.init.body)).isSuggested).toBe(true);
  });

  it("NOT_FOUND uses the neutral card; 'Diễn đạt lại' puts the question back (AC-304.1, AC-304.3)", async () => {
    serve({
      ask: () => ({
        status: 200,
        sse: [
          sseEvent("meta", { questionId: "q", answerId: "a1", readyDocCount: 12, processingDocCount: 0 }),
          sseEvent("done", { status: "NOT_FOUND", reason: "NO_CHUNKS", latencyMs: 10 }),
        ],
      }),
    });
    renderApp("/");
    await askViaComposer("Màu logo?");
    const title = await screen.findByRole("heading", {
      name: /Không tìm thấy thông tin này trong 12 tài liệu hiện có/,
    });
    expect(title.closest("article")).toHaveClass("answer", "not-found");
    expect(title.closest("article")).not.toHaveClass("failed");
    fireEvent.click(screen.getByRole("button", { name: "Diễn đạt lại" }));
    expect(screen.getByLabelText("Câu hỏi về tài liệu")).toHaveValue("Màu logo?");
  });

  it("text already shown is replaced when ALG-3 rejects it (EC-14, AC-306.2)", async () => {
    serve({
      ask: () => ({
        status: 200,
        sse: [
          sseEvent("meta", { questionId: "q", answerId: "a1", readyDocCount: 2, processingDocCount: 0 }),
          sseEvent("delta", { text: "Theo tài liệu, giá là 1 tỷ" }),
          sseEvent("done", { status: "NOT_FOUND", reason: "INVALID_CITATIONS", latencyMs: 10 }),
        ],
      }),
    });
    renderApp("/");
    await askViaComposer("Giá?");
    expect(await screen.findByText(/không có trích dẫn hợp lệ/)).toBeInTheDocument();
    expect(screen.queryByText(/giá là 1 tỷ/)).not.toBeInTheDocument();
  });

  it("a dropped connection keeps the partial answer as incomplete with 'Hỏi lại' (AC-306.3)", async () => {
    serve({
      ask: () => ({
        status: 200,
        failAtEnd: true,
        sse: [
          sseEvent("meta", { questionId: "q", answerId: "a1", readyDocCount: 2, processingDocCount: 0 }),
          sseEvent("delta", { text: "Thanh toán 30% khi ký" }),
        ],
      }),
    });
    renderApp("/");
    await askViaComposer("Thanh toán?");
    expect(await screen.findByText("📶 Câu trả lời chưa hoàn chỉnh do mất kết nối")).toBeInTheDocument();
    expect(screen.getByText(/Thanh toán 30% khi ký/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Hỏi lại" })).toBeInTheDocument();
  });

  it("AI errors show a retry; AI_UNAVAILABLE also raises the outage banner (REL-04)", async () => {
    serve({
      ask: () => ({
        status: 200,
        sse: [
          sseEvent("meta", { questionId: "q", answerId: "a1", readyDocCount: 2, processingDocCount: 0 }),
          sseEvent("error", { code: "AI_UNAVAILABLE", retryable: true }),
        ],
      }),
    });
    renderApp("/");
    await askViaComposer("Giá?");
    expect(await screen.findByText("⚠️ Chưa trả lời được lúc này. Vui lòng thử lại.")).toBeInTheDocument();
    expect(screen.getByText(/Hỏi đáp tạm gián đoạn/)).toBeInTheDocument();
  });

  it("503 AI_BUSY before the stream shows the busy message", async () => {
    serve({ ask: () => ({ status: 503, body: { code: "AI_BUSY" } }) });
    renderApp("/");
    await askViaComposer("Giá?");
    expect(await screen.findByText("Hệ thống đang bận, vui lòng thử lại sau ít giây.")).toBeInTheDocument();
  });
});

describe("US-310 stop", () => {
  it("the send button becomes Dừng while streaming and stops showing text at once", async () => {
    let release!: () => void;
    const gate = new Promise<void>((r) => (release = r));
    const calls = serve({
      me: { flags: ["stream_render"] }, // TQ-01: text is shown while it streams only with this flag
      ask: () => ({
        status: 200,
        sse: [
          sseEvent("meta", { questionId: "q", answerId: "a1", readyDocCount: 2, processingDocCount: 0 }),
          sseEvent("delta", { text: "Một hai ba bốn năm sáu" }),
        ],
      }),
    });
    // keep the stream open until the test releases it
    const realFetch = globalThis.fetch as unknown as (u: string, i: RequestInit) => Promise<Response>;
    vi.stubGlobal("fetch", async (u: string, i: RequestInit) => {
      const res = await realFetch(u, i);
      if (!u.endsWith("/questions")) return res;
      const reader = (res.body as unknown as { getReader(): { read(): Promise<{ done: boolean }> } }).getReader();
      let n = 0;
      return {
        ...res,
        ok: true,
        status: 200,
        body: {
          getReader: () => ({
            read: async () => {
              if (n++ < 2) return reader.read();
              await gate;
              return { done: true, value: undefined };
            },
            cancel: async () => undefined,
          }),
        },
      } as unknown as Response;
    });
    renderApp("/");
    await askViaComposer("Đếm?");
    const stopBtn = await screen.findByRole("button", { name: "Dừng câu trả lời đang soạn" });
    await screen.findByText(/Một hai ba/);
    fireEvent.click(stopBtn);
    await waitFor(() => expect(calls.some((c) => c.url === "/api/v1/answers/a1/stop")).toBe(true));
    await act(async () => release());
    expect(await screen.findByText("⏹ Đã dừng — câu trả lời chưa đầy đủ")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByLabelText("Câu hỏi về tài liệu")).toHaveFocus());
  });
});

describe("US-305 source panel", () => {
  it("clicking [1] opens the cited page with the excerpt highlighted; [2] switches; Esc closes", async () => {
    const rendered: number[] = [];
    pdfMock.open.mockImplementation(async () => ({
      numPages: 9,
      renderPage: async (page: number, _c: HTMLCanvasElement, layer: HTMLElement) => {
        rendered.push(page);
        const spans = ["Điều 5", "Thanh toán 30% khi ký", "hợp đồng"].map((t) => {
          const s = document.createElement("span");
          s.textContent = t;
          layer.append(s);
          return s;
        });
        return spans;
      },
      prefetch: vi.fn(),
      destroy: vi.fn(),
    }));
    serve();
    renderApp("/");
    await askViaComposer("Thanh toán?");
    fireEvent.click(await screen.findByRole("button", { name: "Nguồn 1: Hop-dong-ABC.pdf, trang 3" }));
    await screen.findByText("Trang 3 / 9"); // the lazy panel replaces its loading fallback
    const panel = screen.getByRole("complementary", { name: "Trang nguồn" });
    await waitFor(() => expect(within(panel).getByText("Thanh toán 30% khi ký")).toHaveClass("highlight"));
    expect(pdfMock.open).toHaveBeenCalledWith("/api/v1/documents/d-1/file");
    expect(screen.getByRole("button", { name: "Nguồn 1: Hop-dong-ABC.pdf, trang 3" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(window.location.hash).toBe("#src=d-1:3");

    fireEvent.click(screen.getByRole("button", { name: "Nguồn 2: Bao-gia.pdf, trang 7" })); // AC-305.2
    await screen.findByText("Trang 7 / 9");
    expect(pdfMock.open).toHaveBeenLastCalledWith("/api/v1/documents/d-2/file");

    fireEvent.click(within(panel).getByRole("button", { name: "Trang sau" }));
    await screen.findByText("Trang 8 / 9");
    fireEvent.keyDown(panel, { key: "Escape" });
    expect(screen.queryByRole("complementary", { name: "Trang nguồn" })).not.toBeInTheDocument();
  });

  it("a 404 shows 'vừa được gỡ' and crosses out the citations (EC-15, EC-16)", async () => {
    const { PdfHttpError } = await import("../source-viewer/pdf");
    pdfMock.open.mockRejectedValue(new PdfHttpError(404));
    serve();
    renderApp("/");
    await askViaComposer("Thanh toán?");
    fireEvent.click(await screen.findByRole("button", { name: "Nguồn 1: Hop-dong-ABC.pdf, trang 3" }));
    expect(await screen.findByText("Tài liệu này vừa được gỡ khỏi kho.")).toBeInTheDocument();
    const chip = await screen.findByRole("button", {
      name: "Nguồn 1: Hop-dong-ABC.pdf, trang 3 (tài liệu đã được gỡ)",
    });
    expect(chip).toHaveClass("removed");
  });
});

describe("US-307 / US-309 copy and feedback", () => {
  it("👍 sends HELPFUL once and thanks (AC-309.1)", async () => {
    const calls = serve();
    renderApp("/");
    await askViaComposer("Thanh toán?");
    fireEvent.click(await screen.findByRole("button", { name: "👍 Hữu ích" }));
    expect(await screen.findByText("✓ Cảm ơn phản hồi của bạn")).toBeInTheDocument();
    const fb = calls.filter((c) => c.url.endsWith("/feedback"));
    expect(fb).toHaveLength(1);
    expect(JSON.parse(String(fb[0].init.body))).toEqual({ value: "HELPFUL", reason: null });
  });

  it("👎 opens four reasons; choosing one sends it (AC-309.2)", async () => {
    const calls = serve();
    renderApp("/");
    await askViaComposer("Thanh toán?");
    const down = await screen.findByRole("button", { name: "👎 Chưa tốt" });
    fireEvent.click(down);
    expect(down).toHaveAttribute("aria-expanded", "true");
    const group = screen.getByRole("group", { name: "Vì sao?" });
    expect(within(group).getAllByRole("button")).toHaveLength(4);
    fireEvent.click(within(group).getByRole("button", { name: "Sai nguồn" }));
    await screen.findByText("✓ Cảm ơn phản hồi của bạn");
    expect(JSON.parse(String(calls.find((c) => c.url.endsWith("/feedback"))!.init.body))).toEqual({
      value: "NOT_HELPFUL",
      reason: "wrong_source",
    });
  });

  it("copies the answer with its sources; a blocked clipboard asks to copy by hand (AC-307.1, AC-307.2)", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true });
    serve();
    renderApp("/");
    await askViaComposer("Thanh toán?");
    fireEvent.click(await screen.findByRole("button", { name: "⧉ Sao chép kèm nguồn" }));
    await waitFor(() => expect(writeText).toHaveBeenCalled());
    expect(writeText.mock.calls[0][0]).toBe(
      "Thanh toán 30% khi ký [1].\n\nBảo hành 24 tháng [2].\n\nNguồn:\n[1] Hop-dong-ABC.pdf — trang 3\n[2] Bao-gia.pdf — trang 7",
    );
    writeText.mockRejectedValueOnce(new Error("denied"));
    fireEvent.click(screen.getByRole("button", { name: "⧉ Sao chép kèm nguồn" }));
    expect(
      await screen.findByText("Trình duyệt chặn sao chép tự động. Hãy chọn và sao chép thủ công."),
    ).toBeInTheDocument();
  });
});

describe("US-103 / US-308 session", () => {
  it("an expired session shows the banner and keeps the draft (AC-103.2, EC-17)", async () => {
    serve({ ask: () => ({ status: 401, body: { code: "AUTH_REQUIRED" } }) });
    renderApp("/");
    const box = await screen.findByLabelText("Câu hỏi về tài liệu");
    await waitFor(() => expect(box).not.toBeDisabled());
    fireEvent.change(box, { target: { value: "Câu hỏi đang gõ dở" } });
    expect(sessionStorage.getItem("composer.draft")).toBe("Câu hỏi đang gõ dở");
    fireEvent.keyDown(box, { key: "Enter" });
    expect(await screen.findByRole("button", { name: "Đăng nhập lại" })).toBeInTheDocument();
    expect(screen.getAllByText(/Phiên làm việc đã hết hạn/).length).toBeGreaterThan(0);
  });

  it("the draft is restored after logging in again", async () => {
    sessionStorage.setItem("composer.draft", "Bản nháp cũ");
    serve();
    renderApp("/");
    expect(await screen.findByLabelText("Câu hỏi về tài liệu")).toHaveValue("Bản nháp cũ");
  });

  it("history is restored after a reload when the flag is on (AC-308.1)", async () => {
    sessionStorage.setItem("chat.conversationId", "c-1");
    useChatStore.setState({ conversationId: "c-1", turns: [] });
    mockFetch((url) => {
      if (url === "/api/v1/me") return { status: 200, body: { ...ME, flags: ["history"] } };
      if (url.startsWith("/api/v1/documents?")) return { status: 200, body: { items: [doc()], nextCursor: null } };
      if (url === "/api/v1/conversations/c-1/questions")
        return {
          status: 200,
          body: [
            {
              questionId: "q1",
              text: "Câu cũ?",
              answer: {
                answerId: "a1",
                text: "Trả lời [1]",
                status: "COMPLETED",
                citations: [CITES[0]],
                feedback: null,
              },
            },
          ],
        };
    });
    renderApp("/");
    expect(await screen.findByText("Câu cũ?")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Nguồn 1: Hop-dong-ABC.pdf, trang 3" })).toBeInTheDocument();
  });

  it("follow-up toggle appears only with the flag and sends followUp (US-311)", async () => {
    const user = userEvent.setup();
    const calls = serve({ me: { flags: ["followup"] } });
    renderApp("/");
    await askViaComposer("Giá hợp đồng ABC?");
    await screen.findByRole("button", { name: "Nguồn 1: Hop-dong-ABC.pdf, trang 3" });
    await user.click(screen.getByLabelText("Hỏi tiếp theo ngữ cảnh câu trước"));
    await askViaComposer("Còn bảo hành?");
    await waitFor(() => expect(calls.filter((c) => c.url.endsWith("/questions"))).toHaveLength(2));
    const second = calls.filter((c) => c.url.endsWith("/questions"))[1];
    expect(JSON.parse(String(second.init.body)).followUp).toBe(true);
  });
});

describe("REL-03 kill switch", () => {
  it("flag qa_off disables the composer with the outage banner", async () => {
    serve({ me: { flags: ["qa_off"] } });
    renderApp("/");
    expect((await screen.findAllByText(/Hỏi đáp tạm gián đoạn/)).length).toBeGreaterThan(0);
    await waitFor(() => expect(screen.getByLabelText("Câu hỏi về tài liệu")).toBeDisabled());
  });
});
