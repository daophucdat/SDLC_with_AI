// T-EN12.2 / LG-06 (NFR-01, NFR-02): 100 questions, 10 virtual users, against staging with production sizing.
//
//   k6 run -e BASE_URL=https://staging… -e SESSIONS="<session>:<csrf>,<session>:<csrf>,…" e2e/perf/ask.js
//
// Give one test account per virtual user: the API limits each user to RATE_QUESTIONS_PER_MIN (10) questions,
// and 10 questions per VU fit in that budget only if every VU is a different person — as in real use.
// Thresholds: p95 total ≤ 30 s (NFR-01), p95 first part ≤ 5 s (NFR-02), errors ≤ 2 %.
import http from "k6/http";
import { check, sleep } from "k6";
import { Rate, Trend } from "k6/metrics";

const BASE = __ENV.BASE_URL;
const SESSIONS = (__ENV.SESSIONS || "").split(",").filter(Boolean).map((pair) => pair.split(":"));

const QUESTIONS = [
  "Điều khoản thanh toán của hợp đồng với công ty ABC là gì?",
  "Giá trị hợp đồng ABC là bao nhiêu?",
  "Thời hạn bảo hành phần mềm trong hợp đồng ABC?",
  "Báo giá quý 3 cho XYZ gồm những hạng mục nào?",
  "Công ty DEF yêu cầu tích hợp với hệ thống nào?",
  "What is the expected implementation time in the XYZ quotation?",
  "Phạt chậm thanh toán trong hợp đồng ABC là bao nhiêu?",
  "Logo của công ty ABC màu gì?",
];

const total = new Trend("answer_total_ms", true);
const firstPart = new Trend("answer_first_part_ms", true);
const failed = new Rate("answer_failed");

export const options = {
  scenarios: { ask: { executor: "per-vu-iterations", vus: 10, iterations: 10, maxDuration: "20m" } },
  thresholds: {
    answer_total_ms: ["p(95)<=30000"],
    answer_first_part_ms: ["p(95)<=5000"],
    answer_failed: ["rate<=0.02"],
  },
};

function headers() {
  const [session, csrf] = SESSIONS[(__VU - 1) % SESSIONS.length];
  return {
    "Content-Type": "application/json",
    "X-CSRF-Token": csrf,
    Cookie: `__Host-session=${session}; __Host-csrf=${csrf}`,
  };
}

let conversation = null;

export default function () {
  if (!SESSIONS.length) throw new Error("set SESSIONS");
  if (!conversation) {
    const c = http.post(`${BASE}/api/v1/conversations`, null, { headers: headers() });
    check(c, { "conversation created": (x) => x.status === 201 });
    conversation = c.json("id");
  }
  const q = QUESTIONS[(__VU + __ITER) % QUESTIONS.length];
  const t0 = Date.now();
  const r = http.post(`${BASE}/api/v1/conversations/${conversation}/questions`, JSON.stringify({ text: q }), {
    headers: headers(),
    timeout: "60s",
  });
  total.add(Date.now() - t0);
  const body = r.body || "";
  const ok = r.status === 200 && /event: done/.test(body) && !/event: error/.test(body);
  failed.add(!ok);
  // k6 cannot time individual SSE events, so the first-part time is the server's own measurement
  // (done.firstTokenMs = answer.first_token_ms, the value behind the qa_first_token_seconds histogram).
  const done = /event: done\ndata: (\{.*\})/.exec(body);
  if (done) {
    const meta = JSON.parse(done[1]);
    if (meta.firstTokenMs != null) firstPart.add(meta.firstTokenMs);
  }
  check(r, { "200 + one final event": () => ok });
  sleep(6); // ≤ 10 questions / minute / user (EN-09 rate limit)
}
