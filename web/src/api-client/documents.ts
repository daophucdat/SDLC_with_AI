import { api, ApiError, authRequired, csrfToken, CSRF_HEADER, problemOf } from "./http";
import type { DocumentDto, DocumentListDto, MeDto } from "./types";

export const getMe = () => api<MeDto>("/api/v1/me");

export function listDocuments(params: { q?: string; cursor?: string; limit?: number } = {}) {
  const sp = new URLSearchParams();
  if (params.q && params.q.trim().length >= 2) sp.set("q", params.q.trim());
  if (params.cursor) sp.set("cursor", params.cursor);
  sp.set("limit", String(params.limit ?? 100));
  return api<DocumentListDto>(`/api/v1/documents?${sp}`);
}

export const retryDocument = (id: string) =>
  api<{ id: string; status: string }>(`/api/v1/documents/${id}/retry`, { method: "POST" });

export interface UploadHandle {
  promise: Promise<DocumentDto>;
  abort: () => void;
}

/** Network failures reject with code NETWORK so the queue can pause and retry (EC-04). */
export function uploadDocument(
  file: File,
  opts: { force?: boolean; onProgress?: (pct: number) => void } = {},
): UploadHandle {
  const xhr = new XMLHttpRequest(); // XHR, not fetch: fetch has no upload progress
  const promise = new Promise<DocumentDto>((resolve, reject) => {
    xhr.open("POST", `/api/v1/documents?force=${opts.force ? "true" : "false"}`);
    xhr.withCredentials = true;
    xhr.setRequestHeader("Accept", "application/json");
    const token = csrfToken();
    if (token) xhr.setRequestHeader(CSRF_HEADER, token);
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) opts.onProgress?.(Math.min(100, (e.loaded / e.total) * 100));
    };
    xhr.onerror = () => reject(new ApiError({ status: 0, code: "NETWORK" }));
    xhr.onabort = () => reject(new ApiError({ status: 0, code: "ABORTED" }));
    xhr.onload = () => {
      let body: unknown = null;
      try {
        body = JSON.parse(xhr.responseText);
      } catch {
        /* empty or non-JSON body */
      }
      if (xhr.status >= 200 && xhr.status < 300) return resolve(body as DocumentDto);
      const problem = problemOf(xhr.status, body);
      if (problem.code === "AUTH_REQUIRED") authRequired();
      reject(new ApiError(problem));
    };
    const form = new FormData();
    form.append("file", file, file.name);
    xhr.send(form);
  });
  return { promise, abort: () => xhr.abort() };
}

export const removeDocument = (id: string) =>
  api<{ id: string; status: string }>(`/api/v1/documents/${id}`, { method: "DELETE" });

export const documentFileUrl = (id: string) => `/api/v1/documents/${id}/file`;
