import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { WeeklyMetricDto } from "../api-client/types";
import { axeViolations, fakeResponse, ME, mockFetch, renderApp } from "../test/utils";
import { EvaluationTab } from "./MetricsPage";

afterEach(() => {
  vi.unstubAllGlobals();
});

const LEAD = {
  ...ME,
  role: "BD_LEAD",
  displayName: "Lê Quốc Bảo",
  permissions: ["metrics:view", "evaluation:run"],
  flags: ["evaluation"],
};

function week(i: number, p: Partial<WeeklyMetricDto> = {}): WeeklyMetricDto {
  const start = new Date(Date.UTC(2026, 10, 9 - 7 * i));
  return {
    week: `2026-W${46 - i}`,
    weekStart: start.toISOString().slice(0, 10),
    activeUsers: 19,
    wauRate: 0.63,
    questions: 412,
    notFoundRate: 0.09,
    helpfulRate: 0.74,
    p95LatencyMs: 18400,
    ...p,
  };
}

describe("US-401 metrics page", () => {
  it("shows tiles against the OKR targets and a weekly table; 4 / 8 / 12 weeks (AC-401.1)", async () => {
    const calls = mockFetch((url) => {
      if (url === "/api/v1/me") return { status: 200, body: LEAD };
      const m = /weeks=(\d+)/.exec(url);
      if (m)
        return {
          status: 200,
          body: Array.from({ length: Number(m[1]) }, (_, i) => week(i, i === 0 ? {} : { wauRate: 0.4 })),
        };
    });
    const { container } = renderApp("/metrics");
    expect((await screen.findAllByText("63%"))[0].closest(".tile")).toHaveClass("on");
    expect(screen.getByText(/Mục tiêu ≥ 60% \(KR3.1\)/).closest(".tile")).toHaveClass("on");
    expect(screen.getAllByText("18,4 s").length).toBeGreaterThan(0);
    expect(screen.getAllByRole("row")).toHaveLength(5); // header + 4 weeks
    fireEvent.change(screen.getByLabelText("Khoảng thời gian"), { target: { value: "12" } });
    await waitFor(() => expect(screen.getAllByRole("row")).toHaveLength(13));
    expect(calls.some((c) => c.url.endsWith("weeks=12"))).toBe(true);
    expect(await axeViolations(container)).toEqual([]);
  });

  it("a missed target is shown as not met", async () => {
    mockFetch((url) => {
      if (url === "/api/v1/me") return { status: 200, body: LEAD };
      if (url.includes("/metrics/weekly"))
        return { status: 200, body: [week(0, { wauRate: 0.4, helpfulRate: 0.5 }), week(1), week(2), week(3)] };
    });
    renderApp("/metrics");
    expect((await screen.findByText(/Mục tiêu ≥ 70% \(KR3.2\)/)).closest(".tile")).toHaveClass("off");
  });

  it("members see neither the menu nor the data (AC-401.2)", async () => {
    const calls = mockFetch((url) => (url === "/api/v1/me" ? { status: 200, body: ME } : undefined));
    renderApp("/metrics");
    expect(await screen.findByText("Trang số liệu chỉ dành cho Trưởng nhóm BD và Quản lý.")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Số liệu" })).not.toBeInTheDocument();
    expect(calls.some((c) => c.url.includes("/metrics/weekly"))).toBe(false);
  });

  it("the evaluation tab needs the permission and the flag", async () => {
    mockFetch((url) => {
      if (url === "/api/v1/me") return { status: 200, body: { ...LEAD, flags: [] } };
      if (url.includes("/metrics/weekly")) return { status: 200, body: [week(0)] };
    });
    renderApp("/metrics");
    await screen.findByRole("tab", { name: "Số liệu sử dụng" });
    expect(screen.queryByRole("tab", { name: "Nghiệm thu chất lượng" })).not.toBeInTheDocument();
  });
});

describe("US-402 evaluation tab", () => {
  it("uploads, shows progress, then offers the export (AC-402.1)", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    let done = 0;
    mockFetch((url) => {
      if (url === "/api/v1/evaluations") return { status: 202, body: { runId: "r1", total: 2 } };
      if (url === "/api/v1/evaluations/r1") {
        done += 1;
        return { status: 200, body: { runId: "r1", status: done >= 2 ? "done" : "running", done, total: 2 } };
      }
    });
    render(<EvaluationTab pollMs={20} />);
    fireEvent.change(screen.getByLabelText("File bộ câu hỏi"), {
      target: { files: [new File(["x"], "bo.xlsx")] },
    });
    fireEvent.click(screen.getByRole("button", { name: "Chạy nghiệm thu" }));
    expect(await screen.findByText("Đang chạy… 0/2 câu")).toBeInTheDocument();
    expect(await screen.findByText(/Đã chạy xong 2\/2 câu/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "⬇ Tải kết quả (.xlsx)" })).toHaveAttribute(
      "href",
      "/api/v1/evaluations/r1/export",
    );
    vi.useRealTimers();
  });

  it("names the row and column of an invalid file (AC-402.2)", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => fakeResponse(400, JSON.stringify({ code: "TESTSET_INVALID", row: 12, column: "Câu hỏi" }))),
    );
    render(<EvaluationTab />);
    fireEvent.change(screen.getByLabelText("File bộ câu hỏi"), { target: { files: [new File(["x"], "bad.xlsx")] } });
    fireEvent.click(screen.getByRole("button", { name: "Chạy nghiệm thu" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Dòng 12: thiếu cột Câu hỏi.");
  });
});
