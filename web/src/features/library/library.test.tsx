import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { DocumentDto } from "../../api-client/types";
import { axeViolations, doc, ME, mockFetch, renderApp } from "../../test/utils";

vi.mock("../../analytics/track", () => ({ track: vi.fn() }));

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

function serve(
  docs: () => DocumentDto[],
  extra: (url: string, init: RequestInit) => { status: number; body?: unknown } | undefined = () => undefined,
) {
  return mockFetch((url, init) => {
    if (url === "/api/v1/me") return { status: 200, body: ME };
    if (url.startsWith("/api/v1/documents?")) return { status: 200, body: { items: docs(), nextCursor: null } };
    return extra(url, init);
  });
}

describe("US-202 library list", () => {
  it("shows every status with plain-language messages (AC-202.3) and passes axe", async () => {
    serve(() => [
      doc({ id: "a", fileName: "San-sang.pdf" }),
      doc({ id: "b", fileName: "Dang-xu-ly.pdf", status: "PROCESSING", pageCount: null }),
      doc({ id: "c", fileName: "Scan.pdf", status: "NO_TEXT" }),
      doc({
        id: "d",
        fileName: "Mat-khau.pdf",
        status: "ERROR",
        errorCode: "PASSWORD",
        uploadedBy: { id: "u-2", displayName: "Lê Quốc Bảo" },
      }),
    ]);
    const { container } = renderApp("/");
    expect(await screen.findByText("San-sang.pdf")).toBeInTheDocument();
    expect(screen.getByText("Sẵn sàng")).toBeInTheDocument();
    expect(screen.getByText("Có thể hỏi khi tài liệu sẵn sàng.")).toBeInTheDocument();
    expect(screen.getByText(/ảnh scan/)).toBeInTheDocument();
    expect(screen.getByText("File có mật khẩu. Hãy gỡ mật khẩu rồi tải lại.")).toBeInTheDocument();
    expect(screen.getAllByText(/^Bạn ·/)).toHaveLength(3);
    expect(screen.getByText(/^Lê Quốc Bảo ·/)).toBeInTheDocument();
    expect(await axeViolations(container)).toEqual([]);
  });

  it("Thử lại on an ERROR document calls the retry endpoint with CSRF", async () => {
    document.cookie = "csrf=tok";
    let status: DocumentDto["status"] = "ERROR";
    const calls = serve(
      () => [doc({ id: "e1", fileName: "Hong.pdf", status, errorCode: status === "ERROR" ? "CORRUPT" : null })],
      (url) => {
        if (url === "/api/v1/documents/e1/retry") {
          status = "PROCESSING";
          return { status: 202, body: { id: "e1", status: "PROCESSING" } };
        }
      },
    );
    const user = userEvent.setup();
    renderApp("/");
    await user.click(await screen.findByRole("button", { name: "Tuỳ chọn cho Hong.pdf" }));
    await user.click(screen.getByRole("menuitem", { name: "Thử lại" }));
    await waitFor(() => expect(screen.getByText("Đang xử lý")).toBeInTheDocument());
    const retry = calls.find((c) => c.url.endsWith("/retry"))!;
    expect(retry.init.method).toBe("POST");
    expect(new Headers(retry.init.headers).get("X-CSRF-Token")).toBe("tok");
    document.cookie = "csrf=; expires=Thu, 01 Jan 1970 00:00:00 GMT";
  });

  it("polls while a document is processing and toasts when it becomes ready (T202.3, T202.5)", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    let status: DocumentDto["status"] = "PROCESSING";
    const calls = serve(() => [doc({ id: "p", fileName: "Bao-gia.pdf", status })]);
    renderApp("/");
    expect(await screen.findByText("Đang xử lý")).toBeInTheDocument();
    const listCalls = () => calls.filter((c) => c.url.startsWith("/api/v1/documents?")).length;
    const before = listCalls();

    status = "READY";
    await vi.advanceTimersByTimeAsync(3100);
    expect(await screen.findByText("“Bao-gia.pdf” đã sẵn sàng để hỏi")).toBeInTheDocument();
    expect(listCalls()).toBe(before + 1);

    await vi.advanceTimersByTimeAsync(10_000); // nothing processing → polling stops
    expect(listCalls()).toBe(before + 1);
  });

  it("filter sends q only from 2 characters", async () => {
    const calls = serve(() => []);
    const user = userEvent.setup();
    renderApp("/");
    await screen.findByText("Kho chưa có tài liệu");
    await user.type(screen.getByLabelText("Lọc theo tên"), "h");
    await user.type(screen.getByLabelText("Lọc theo tên"), "d");
    await waitFor(() => expect(calls.some((c) => c.url.includes("q=hd"))).toBe(true));
    expect(calls.some((c) => /q=h(&|$)/.test(c.url))).toBe(false);
    expect(await screen.findByText("Không có tài liệu khớp bộ lọc.")).toBeInTheDocument();
  });
});

describe("US-201 upload", () => {
  class FakeXhr {
    static last: FakeXhr[] = [];
    upload: { onprogress?: (e: { lengthComputable: boolean; loaded: number; total: number }) => void } = {};
    onload?: () => void;
    onerror?: () => void;
    onabort?: () => void;
    status = 0;
    responseText = "";
    withCredentials = false;
    headers: Record<string, string> = {};
    url = "";
    open(_m: string, url: string) {
      this.url = url;
    }
    setRequestHeader(k: string, v: string) {
      this.headers[k] = v;
    }
    send() {
      FakeXhr.last.push(this);
    }
    abort() {
      this.onabort?.();
    }
    respond(status: number, body: unknown) {
      this.status = status;
      this.responseText = JSON.stringify(body);
      this.onload?.();
    }
  }

  beforeEach(() => {
    FakeXhr.last = [];
    vi.stubGlobal("XMLHttpRequest", FakeXhr);
  });

  const pick = (files: File[]) => fireEvent.change(screen.getByTestId("file-input"), { target: { files } });

  it("a picked PDF shows 'Đang tải lên' with %, then becomes a PROCESSING row (AC-201.1)", async () => {
    let docs: DocumentDto[] = [];
    serve(() => docs);
    renderApp("/");
    await screen.findByText("Kho chưa có tài liệu");

    pick([new File(["%PDF-1.7"], "Hop-dong.pdf", { type: "application/pdf" })]);
    const xhr = FakeXhr.last[0];
    expect(xhr.url).toBe("/api/v1/documents?force=false");
    xhr.upload.onprogress?.({ lengthComputable: true, loaded: 40, total: 100 });
    const row = await screen.findByText("Hop-dong.pdf");
    expect(within(row.closest("li")!).getByText("Đang tải lên 40%")).toBeInTheDocument();
    expect(screen.getByRole("progressbar", { name: "Tiến độ tải Hop-dong.pdf" })).toHaveAttribute(
      "aria-valuenow",
      "40",
    );

    docs = [doc({ id: "n", fileName: "Hop-dong.pdf", status: "PROCESSING" })];
    xhr.respond(202, docs[0]);
    expect(await screen.findByText("Đang xử lý")).toBeInTheDocument();
  });

  it("a non-PDF is refused on the client with a toast, no request sent", async () => {
    serve(() => []);
    renderApp("/");
    await screen.findByText("Kho chưa có tài liệu");
    pick([new File(["x"], "anh.png", { type: "image/png" })]);
    expect(await screen.findByText("anh.png: Chỉ hỗ trợ file PDF.")).toBeInTheDocument();
    expect(FakeXhr.last).toHaveLength(0);
  });

  it("duplicate → ConfirmDialog; 'Vẫn tải lên' resends with force=true", async () => {
    serve(() => []);
    const user = userEvent.setup();
    renderApp("/");
    await screen.findByText("Kho chưa có tài liệu");
    pick([new File(["%PDF-1.7"], "Trung.pdf", { type: "application/pdf" })]);
    FakeXhr.last[0].respond(409, { code: "DUPLICATE_DOCUMENT", existingId: "d-1", uploadedAt: "2026-10-01T09:00:00Z" });

    const dialog = await screen.findByRole("alertdialog", { name: "File đã có trong kho" });
    expect(dialog).toHaveTextContent("tải lên ngày 1/10/2026");
    await user.click(within(dialog).getByRole("button", { name: "Vẫn tải lên" }));
    expect(FakeXhr.last[1].url).toBe("/api/v1/documents?force=true");
  });
});
