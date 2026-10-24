import { api, csrfToken, CSRF_HEADER, problemOf, ApiError } from "./http";
import { postSse } from "./sse";
import type { EvaluationStatusDto, TurnDto, WeeklyMetricDto } from "./types";

export const createConversation = () => api<{ id: string }>("/api/v1/conversations", { method: "POST" });

export const askQuestion = (
  conversationId: string,
  body: { text: string; followUp?: boolean; isSuggested?: boolean },
  signal?: AbortSignal,
) => postSse(`/api/v1/conversations/${conversationId}/questions`, body, signal);

export const getHistory = (conversationId: string) =>
  api<TurnDto[]>(`/api/v1/conversations/${conversationId}/questions`);

export const stopAnswer = (answerId: string) => api<void>(`/api/v1/answers/${answerId}/stop`, { method: "POST" });

export const sendFeedback = (answerId: string, value: "HELPFUL" | "NOT_HELPFUL", reason?: string) =>
  api<void>(`/api/v1/answers/${answerId}/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ value, reason: reason ?? null }),
  });

export const getWeeklyMetrics = (weeks: number) => api<WeeklyMetricDto[]>(`/api/v1/metrics/weekly?weeks=${weeks}`);

export async function startEvaluation(file: File): Promise<{ runId: string; total: number }> {
  const form = new FormData();
  form.append("file", file, file.name);
  const headers = new Headers({ Accept: "application/json" });
  const token = csrfToken();
  if (token) headers.set(CSRF_HEADER, token);
  const res = await fetch("/api/v1/evaluations", { method: "POST", body: form, headers, credentials: "same-origin" });
  if (!res.ok) throw new ApiError(problemOf(res.status, await res.json().catch(() => null)));
  return res.json();
}

export const getEvaluation = (runId: string) => api<EvaluationStatusDto>(`/api/v1/evaluations/${runId}`);

export const evaluationExportUrl = (runId: string) => `/api/v1/evaluations/${runId}/export`;
export const evaluationTemplateUrl = "/api/v1/evaluations-template";
