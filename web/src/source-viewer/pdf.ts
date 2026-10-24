// PDF.js wrapper (T305.2). Loaded lazily with the source panel. Range requests + no auto-fetch: only the bytes of the
// pages that are shown are downloaded, which is what keeps "open the cited page" ≤ 2 s on a 50 MB file (NFR-05).
export interface PdfDoc {
  numPages: number;
  /** Renders the page into the canvas, builds the text layer, returns the text-layer elements in reading order. */
  renderPage(
    pageNumber: number,
    canvas: HTMLCanvasElement,
    textLayer: HTMLElement,
    width: number,
  ): Promise<HTMLElement[]>;
  prefetch(pageNumber: number): void;
  destroy(): void;
}

export class PdfHttpError extends Error {
  constructor(public readonly status: number) {
    super(`HTTP ${status}`);
  }
}

export async function openPdf(url: string): Promise<PdfDoc> {
  const pdfjs = await import("pdfjs-dist");
  pdfjs.GlobalWorkerOptions.workerSrc = new URL("pdfjs-dist/build/pdf.worker.min.js", import.meta.url).toString();
  const task = pdfjs.getDocument({
    url,
    rangeChunkSize: 65536,
    disableAutoFetch: true,
    disableStream: true,
    withCredentials: true,
  });
  let doc;
  try {
    doc = await task.promise;
  } catch (e) {
    const status = (e as { status?: number })?.status;
    throw status ? new PdfHttpError(status) : e;
  }
  return {
    numPages: doc.numPages,
    async renderPage(n, canvas, textLayer, width) {
      const page = await doc.getPage(n);
      const base = page.getViewport({ scale: 1 });
      const viewport = page.getViewport({ scale: width / base.width });
      const ratio = window.devicePixelRatio || 1;
      canvas.width = Math.floor(viewport.width * ratio);
      canvas.height = Math.floor(viewport.height * ratio);
      canvas.style.width = `${viewport.width}px`;
      canvas.style.height = `${viewport.height}px`;
      const ctx = canvas.getContext("2d")!;
      ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
      await page.render({ canvasContext: ctx, viewport }).promise;
      textLayer.replaceChildren();
      textLayer.style.width = `${viewport.width}px`;
      textLayer.style.height = `${viewport.height}px`;
      textLayer.style.setProperty("--scale-factor", String(viewport.scale));
      const textDivs: HTMLElement[] = [];
      const textContent = await page.getTextContent();
      await pdfjs.renderTextLayer({ textContentSource: textContent, container: textLayer, viewport, textDivs }).promise;
      return textDivs;
    },
    prefetch(n) {
      if (n >= 1 && n <= doc.numPages) doc.getPage(n).catch(() => undefined);
    },
    destroy() {
      task.destroy();
    },
  };
}

const norm = (s: string) => s.normalize("NFC").replace(/\s+/g, " ").trim().toLowerCase();

/** T305.3: indices of the text-layer items covered by the excerpt (first 80 normalised chars), or [] if not found. */
export function findExcerpt(items: string[], excerpt: string): number[] {
  const needle = norm(excerpt).slice(0, 80);
  if (needle.length < 8) return [];
  let joined = "";
  const owner: number[] = [];
  items.forEach((raw, i) => {
    const t = norm(raw);
    if (!t) return;
    if (joined) {
      joined += " ";
      owner.push(i);
    }
    for (let k = 0; k < t.length; k++) owner.push(i);
    joined += t;
  });
  const at = joined.indexOf(needle);
  if (at < 0) return [];
  return [...new Set(owner.slice(at, at + needle.length))];
}
