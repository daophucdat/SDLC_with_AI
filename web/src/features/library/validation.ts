// Client-side pre-check (US-201 T201.5). The server checks again: a renamed non-PDF still gets 415.
export const MAX_UPLOAD_MB = 50;

export type RejectReason = "FILE_NOT_PDF" | "FILE_TOO_LARGE";

export function precheck(file: File): RejectReason | null {
  const looksPdf = file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");
  if (!looksPdf) return "FILE_NOT_PDF";
  if (file.size > MAX_UPLOAD_MB * 1024 * 1024) return "FILE_TOO_LARGE";
  return null;
}
