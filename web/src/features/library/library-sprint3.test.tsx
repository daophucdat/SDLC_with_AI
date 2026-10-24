import { act, fireEvent, screen, waitFor, within } from "@testing-library/react";
import type { DocumentDto } from "../../api-client/types";
import { useChatStore } from "../../state/chatStore";
import { doc, ME, mockFetch, renderApp } from "../../test/utils";

vi.mock("../../analytics/track", () => ({ track: vi.fn() }));

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});
beforeEach(() => useChatStore.getState().reset());

function serve(
  docs: () => DocumentDto[],
  extra: (url: string, init: RequestInit) => { status: number; body?: unknown } | undefined = () => undefined,
) {
  return mockFetch((url, init) => {
    if (url === "/api/v1/me") return { status: 200, body: ME };
    if (url.startsWith("/api/v1/documents?")) {
      const q = new URL(url, "http://x").searchParams.get("q");
      const items = docs().filter((d) => !q || d.fileName.toLowerCase().includes(q.toLowerCase()));
      return { status: 200, body: { items, nextCursor: null } };
    }
    return extra(url, init);
  });
}

describe("US-204 remove", () => {
  it("menu item only when canRemove; dialog focuses Huỷ; confirm removes at once and toasts (AC-204.1, AC-204.2)", async () => {
    let docs = [
      doc({ id: "mine", fileName: "Cua-toi.pdf", canRemove: true }),
      doc({
        id: "theirs",
        fileName: "Cua-ban.pdf",
        canRemove: false,
        uploadedBy: { id: "u-2", displayName: "Lê Quốc Bảo" },
      }),
    ];
    const calls = serve(
      () => docs,
      (url, init) => {
        if (url === "/api/v1/documents/mine" && init.method === "DELETE") {
          docs = docs.filter((d) => d.id !== "mine");
          return { status: 202, body: { id: "mine", status: "REMOVED" } };
        }
      },
    );
    renderApp("/");
    expect(await screen.findByText("Cua-ban.pdf")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Tuỳ chọn cho Cua-ban.pdf" })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Tuỳ chọn cho Cua-toi.pdf" }));
    fireEvent.click(screen.getByRole("menuitem", { name: "Gỡ khỏi kho" }));
    const dialog = screen.getByRole("alertdialog", { name: "Gỡ tài liệu?" });
    expect(dialog).toHaveTextContent("sẽ không còn được dùng cho câu trả lời mới của cả đội");
    expect(within(dialog).getByRole("button", { name: "Huỷ" })).toHaveFocus();
    fireEvent.click(within(dialog).getByRole("button", { name: "Gỡ tài liệu" }));

    await waitFor(() => expect(screen.queryByText("Cua-toi.pdf")).not.toBeInTheDocument());
    expect(await screen.findByText("Đã gỡ “Cua-toi.pdf”")).toBeInTheDocument();
    expect(calls.find((c) => c.init.method === "DELETE")?.url).toBe("/api/v1/documents/mine");
    expect(useChatStore.getState().removedDocIds.has("mine")).toBe(true);
  });

  it("a refused removal puts the row back", async () => {
    serve(
      () => [doc({ id: "x", fileName: "X.pdf" })],
      (_url, init) => (init.method === "DELETE" ? { status: 403, body: { code: "FORBIDDEN" } } : undefined),
    );
    renderApp("/");
    fireEvent.click(await screen.findByRole("button", { name: "Tuỳ chọn cho X.pdf" }));
    fireEvent.click(screen.getByRole("menuitem", { name: "Gỡ khỏi kho" }));
    fireEvent.click(screen.getByRole("button", { name: "Gỡ tài liệu" }));
    expect(await screen.findByText("Bạn không có quyền thực hiện thao tác này.")).toBeInTheDocument();
    expect(screen.getByText("X.pdf")).toBeInTheDocument();
  });
});

describe("US-203 filter", () => {
  it("debounces 250 ms, needs 2 characters, offers 'Xoá bộ lọc' (AC-203.2)", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const calls = serve(() => [
      doc({ id: "1", fileName: "Hop-dong-ABC.pdf" }),
      doc({ id: "2", fileName: "Bao-gia.pdf" }),
    ]);
    renderApp("/");
    await screen.findByText("Bao-gia.pdf");
    const box = screen.getByLabelText("Lọc theo tên");
    fireEvent.change(box, { target: { value: "h" } });
    fireEvent.change(box, { target: { value: "ho" } });
    fireEvent.change(box, { target: { value: "hop" } });
    await act(async () => void (await vi.advanceTimersByTimeAsync(100)));
    expect(calls.some((c) => c.url.includes("q=hop"))).toBe(false);
    await act(async () => void (await vi.advanceTimersByTimeAsync(300)));
    await waitFor(() => expect(screen.queryByText("Bao-gia.pdf")).not.toBeInTheDocument());
    expect(calls.filter((c) => /q=h(&|$)/.test(c.url))).toHaveLength(0);

    fireEvent.change(box, { target: { value: "zzz" } });
    await act(async () => void (await vi.advanceTimersByTimeAsync(300)));
    expect(await screen.findByText("Không có tài liệu khớp bộ lọc.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Xoá bộ lọc" }));
    expect(box).toHaveValue("");
    await act(async () => void (await vi.advanceTimersByTimeAsync(300)));
    expect(await screen.findByText("Bao-gia.pdf")).toBeInTheDocument();
  });
});

describe("US-205 no text", () => {
  it("PROCESSING → NO_TEXT shows the warning badge and a toast (T205.2)", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    let status: DocumentDto["status"] = "PROCESSING";
    serve(() => [doc({ id: "s", fileName: "Scan.pdf", status })]);
    renderApp("/");
    await screen.findByText("Đang xử lý");
    status = "NO_TEXT";
    await act(async () => void (await vi.advanceTimersByTimeAsync(3100)));
    expect(await screen.findByText("“Scan.pdf” là file dạng ảnh scan, không đọc được chữ")).toBeInTheDocument();
    expect(screen.getByText("Không đọc được chữ")).toHaveClass("badge", "badge-warning");
    expect(screen.getByText(/ảnh scan, không được dùng để trả lời/)).toBeInTheDocument();
  });
});
