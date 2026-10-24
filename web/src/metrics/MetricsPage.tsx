// MetricsPage (T401.3) + EvaluationTab (US-402), as metrics.html. Visible to BD lead and manager only.
import { useQuery } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import type { KeyboardEvent } from "react";
import { ApiError } from "../api-client/http";
import {
  evaluationExportUrl,
  evaluationTemplateUrl,
  getEvaluation,
  getWeeklyMetrics,
  startEvaluation,
} from "../api-client/qa";
import type { EvaluationStatusDto, WeeklyMetricDto } from "../api-client/types";
import { useMe } from "../auth/RequireAuth";
import { fmt, vi } from "../i18n/vi";
import { AppShell, Badge, Button, EmptyState, ProgressBar, Select, Spinner } from "../ui";

const pct = (v: number | null | undefined) => (v == null ? "—" : `${Math.round(v * 100)}%`);
const secs = (ms: number | null | undefined) =>
  ms == null ? "—" : `${(ms / 1000).toLocaleString("vi-VN", { maximumFractionDigits: 1 })} s`;

function weekLabel(m: WeeklyMetricDto): string {
  const start = new Date(m.weekStart);
  const end = new Date(start.getTime() + 6 * 86400000);
  const f = (d: Date) => d.toLocaleDateString("vi-VN", { day: "2-digit", month: "2-digit" });
  return `${vi.metrics.week} ${m.week.split("-W")[1]} (${f(start)} – ${f(end)})`;
}

function Tile({ label, value, target, ok }: { label: string; value: string; target: string; ok?: boolean | null }) {
  const cls = ok == null ? "tile" : ok ? "tile on" : "tile off";
  return (
    <div className={cls}>
      <span className="tile-label">{label}</span>
      <span className="tile-value">{value}</span>
      <span className={`tile-target${ok == null ? " muted" : ""}`}>
        {ok == null ? target : `${ok ? "✓" : "✗"} ${target}`}
      </span>
    </div>
  );
}

function UsageTab() {
  const [weeks, setWeeks] = useState(4);
  const q = useQuery({ queryKey: ["metrics", weeks], queryFn: () => getWeeklyMetrics(weeks) });
  if (q.isPending) return <Spinner label="Đang tải số liệu" />;
  if (q.isError) return <EmptyState icon="⚠️" title={vi.errors.INTERNAL} />;
  const rows = q.data;
  const cur = rows[0];
  const hasData = rows.some((r) => r.questions > 0);
  return (
    <>
      <div className="row" style={{ justifyContent: "flex-end", marginBottom: "var(--space-4)" }}>
        <div className="field" style={{ width: 200 }}>
          <label htmlFor="weeks">{vi.metrics.weeks}</label>
          <Select id="weeks" value={weeks} onChange={(e) => setWeeks(Number(e.target.value))}>
            {[4, 8, 12].map((n) => (
              <option key={n} value={n}>
                {fmt(vi.metrics.weeksOption, { n })}
              </option>
            ))}
          </Select>
        </div>
      </div>
      {!hasData ? (
        <EmptyState icon="📊" title={vi.metrics.noData} />
      ) : (
        <div className="grid grid-4" style={{ marginBottom: "var(--space-6)" }}>
          <Tile
            label={vi.metrics.wau}
            value={pct(cur.wauRate)}
            target={`${vi.metrics.targetWau} · ${cur.activeUsers} người`}
            ok={cur.wauRate >= 0.6}
          />
          <Tile
            label={vi.metrics.p95}
            value={secs(cur.p95LatencyMs)}
            target={vi.metrics.targetP95}
            ok={cur.p95LatencyMs == null ? null : cur.p95LatencyMs <= 30000}
          />
          <Tile
            label={vi.metrics.helpful}
            value={pct(cur.helpfulRate)}
            target={vi.metrics.targetHelpful}
            ok={cur.helpfulRate == null ? null : cur.helpfulRate >= 0.7}
          />
          <Tile label={vi.metrics.notFound} value={pct(cur.notFoundRate)} target={vi.metrics.track} />
          <Tile label={vi.metrics.questions} value={String(cur.questions)} target="" />
        </div>
      )}
      <table className="table">
        <caption className="sr-only">Số liệu theo tuần</caption>
        <thead>
          <tr>
            <th scope="col">{vi.metrics.week}</th>
            <th className="num" scope="col">
              {vi.metrics.wau}
            </th>
            <th className="num" scope="col">
              Câu hỏi
            </th>
            <th className="num" scope="col">
              “Không tìm thấy”
            </th>
            <th className="num" scope="col">
              “Hữu ích”
            </th>
            <th className="num" scope="col">
              p95
            </th>
          </tr>
        </thead>
        <tbody>
          {[...rows].reverse().map((m) => (
            <tr key={m.week}>
              <td>{weekLabel(m)}</td>
              <td className="num">{pct(m.wauRate)}</td>
              <td className="num">{m.questions}</td>
              <td className="num">{pct(m.notFoundRate)}</td>
              <td className="num">{pct(m.helpfulRate)}</td>
              <td className="num">{secs(m.p95LatencyMs)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="xs muted" style={{ marginTop: "var(--space-2)" }}>
        {vi.metrics.denominator}
      </p>
    </>
  );
}

export function EvaluationTab({ pollMs = 3000 }: { pollMs?: number }) {
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [run, setRun] = useState<EvaluationStatusDto | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!run || run.status === "done" || run.status === "timeout" || run.status === "failed") return;
    const t = setInterval(async () => {
      try {
        setRun(await getEvaluation(run.runId));
      } catch {
        /* keep polling */
      }
    }, pollMs);
    return () => clearInterval(t);
  }, [run, pollMs]);

  const start = async () => {
    if (!file) return setError(vi.evaluation.pickFile);
    setBusy(true);
    setError(null);
    try {
      const r = await startEvaluation(file);
      setRun({ runId: r.runId, status: "queued", done: 0, total: r.total });
    } catch (e) {
      if (e instanceof ApiError && e.code === "TESTSET_INVALID")
        setError(
          fmt(vi.evaluation.invalid, { row: String(e.problem.row ?? "?"), column: String(e.problem.column ?? "?") }),
        );
      else setError(vi.errors.INTERNAL);
    } finally {
      setBusy(false);
    }
  };

  const finished = run && ["done", "timeout", "failed"].includes(run.status);
  return (
    <div className="grid grid-2">
      <div className="card">
        <h2 style={{ fontSize: "var(--text-lg)" }}>{vi.evaluation.title}</h2>
        <p className="small muted">{vi.evaluation.help}</p>
        <div className="field" style={{ marginBottom: "var(--space-3)" }}>
          <label htmlFor="testset">{vi.evaluation.file}</label>
          <input
            className="input"
            type="file"
            id="testset"
            accept=".xlsx"
            aria-describedby={error ? "eval-error" : undefined}
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
        </div>
        {error && (
          <p className="xs" id="eval-error" role="alert" style={{ color: "var(--color-danger)" }}>
            {error}
          </p>
        )}
        <div className="row">
          <Button variant="primary" onClick={start} disabled={busy || (!!run && !finished)}>
            {vi.evaluation.run}
          </Button>
          <a className="btn btn-ghost" href={evaluationTemplateUrl}>
            {vi.evaluation.template}
          </a>
        </div>
        {run && !finished && (
          <div style={{ marginTop: "var(--space-4)" }}>
            <div className="small" role="status">
              {fmt(vi.evaluation.running, { done: run.done, total: run.total })}
            </div>
            <ProgressBar value={run.total ? (run.done / run.total) * 100 : 0} label={vi.evaluation.progress} />
          </div>
        )}
      </div>
      <div className="card">
        {finished ? (
          <>
            <p role="status">
              <Badge tone={run!.status === "done" ? "ready" : "warning"}>{run!.status}</Badge>{" "}
              {fmt(run!.status === "timeout" ? vi.evaluation.timeout : vi.evaluation.done, {
                done: run!.done,
                total: run!.total,
              })}
            </p>
            <a className="btn btn-secondary" href={evaluationExportUrl(run!.runId)}>
              {vi.evaluation.export}
            </a>
          </>
        ) : (
          <EmptyState icon="🧪" title={vi.evaluation.title} />
        )}
      </div>
    </div>
  );
}

export function MetricsPage() {
  const me = useMe();
  const canView = me.permissions.includes("metrics:view");
  const canEvaluate = me.permissions.includes("evaluation:run") && me.flags.includes("evaluation");
  const [tab, setTab] = useState<"usage" | "eval">("usage");
  const tabs = useRef<(HTMLButtonElement | null)[]>([]);

  const logout = async () => {
    await fetch("/auth/logout", { method: "POST" }).catch(() => undefined);
    window.location.assign("/login");
  };

  const onTabKey = (e: KeyboardEvent) => {
    if (!canEvaluate || (e.key !== "ArrowRight" && e.key !== "ArrowLeft")) return;
    const next = tab === "usage" ? "eval" : "usage";
    setTab(next);
    tabs.current[next === "usage" ? 0 : 1]?.focus();
  };

  return (
    <AppShell me={me} onLogout={logout}>
      <div className="doc-page" style={{ overflowY: "auto" }}>
        <h1>{vi.metrics.title}</h1>
        {!canView ? (
          <EmptyState icon="🔒" title={vi.metrics.forbidden} />
        ) : (
          <>
            <div className="tabs" role="tablist" aria-label="Chế độ xem" onKeyDown={onTabKey}>
              <button
                ref={(el) => (tabs.current[0] = el)}
                className="tab"
                role="tab"
                id="tab-usage"
                aria-selected={tab === "usage"}
                aria-controls="panel-usage"
                tabIndex={tab === "usage" ? 0 : -1}
                onClick={() => setTab("usage")}
              >
                {vi.metrics.usageTab}
              </button>
              {canEvaluate && (
                <button
                  ref={(el) => (tabs.current[1] = el)}
                  className="tab"
                  role="tab"
                  id="tab-eval"
                  aria-selected={tab === "eval"}
                  aria-controls="panel-eval"
                  tabIndex={tab === "eval" ? 0 : -1}
                  onClick={() => setTab("eval")}
                >
                  {vi.metrics.evalTab}
                </button>
              )}
            </div>
            {tab === "usage" ? (
              <section role="tabpanel" id="panel-usage" aria-labelledby="tab-usage">
                <UsageTab />
              </section>
            ) : (
              <section role="tabpanel" id="panel-eval" aria-labelledby="tab-eval">
                <EvaluationTab />
              </section>
            )}
          </>
        )}
      </div>
    </AppShell>
  );
}
