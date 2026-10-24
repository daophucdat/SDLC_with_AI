// Keep in sync with backend/chatdocs/adapters/http/schemas.py (dev_tasks.md §0.4)
export type Role = "BD_MEMBER" | "BD_LEAD" | "MANAGER";
export type DocumentStatus = "UPLOADING" | "PROCESSING" | "READY" | "NO_TEXT" | "ERROR";
export type ProcessingErrorCode = "PASSWORD" | "CORRUPT" | "NOT_PDF" | "TIMEOUT" | "INTERNAL";

export interface MeDto {
  id: string;
  displayName: string;
  email: string;
  role: Role;
  permissions: string[];
  flags: string[];
}

export interface DocumentDto {
  id: string;
  fileName: string;
  pageCount: number | null;
  status: DocumentStatus;
  errorCode?: ProcessingErrorCode | null;
  uploadedBy: { id: string; displayName: string };
  uploadedAt: string;
  canRemove: boolean;
}

export interface DocumentListDto {
  items: DocumentDto[];
  nextCursor: string | null;
}

export interface Problem {
  type?: string;
  title?: string;
  status: number;
  code: string;
  traceId?: string | null;
  [extra: string]: unknown;
}

export interface CitationDto {
  index: number;
  documentId: string;
  fileName: string;
  page: number;
  excerpt: string;
  removed: boolean;
}

export type AnswerFinalStatus = "COMPLETED" | "NOT_FOUND" | "STOPPED" | "FAILED";
export type NotFoundReason = "NO_CHUNKS" | "MODEL_NOT_FOUND" | "INVALID_CITATIONS";

export interface TurnDto {
  questionId: string;
  text: string;
  answer: {
    answerId: string;
    text: string;
    status: AnswerFinalStatus | "STREAMING";
    citations: CitationDto[];
    feedback?: "HELPFUL" | "NOT_HELPFUL" | null;
  };
}

export interface WeeklyMetricDto {
  week: string;
  weekStart: string;
  activeUsers: number;
  wauRate: number;
  questions: number;
  notFoundRate: number;
  helpfulRate: number | null;
  p95LatencyMs: number | null;
}

export interface EvaluationStatusDto {
  runId: string;
  status: "queued" | "running" | "done" | "failed" | "timeout";
  done: number;
  total: number;
}
