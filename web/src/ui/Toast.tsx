// Toast + useToast (EN-11 T-EN11.3): role=status, auto-hide after 5 s.
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import { vi } from "../i18n/vi";

export type ToastKind = "info" | "success" | "error";
interface ToastItem {
  id: number;
  message: string;
  kind: ToastKind;
  action?: { label: string; onClick: () => void };
}
type Show = (message: string, kind?: ToastKind, action?: ToastItem["action"]) => void;

const ToastContext = createContext<Show | null>(null);
export const TOAST_MS = 5000;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const nextId = useRef(1);
  const timers = useRef(new Map<number, ReturnType<typeof setTimeout>>());

  const dismiss = useCallback((id: number) => {
    setItems((xs) => xs.filter((t) => t.id !== id));
    clearTimeout(timers.current.get(id));
    timers.current.delete(id);
  }, []);

  const show = useCallback<Show>(
    (message, kind = "info", action) => {
      const id = nextId.current++;
      setItems((xs) => [...xs, { id, message, kind, action }]);
      timers.current.set(
        id,
        setTimeout(() => dismiss(id), TOAST_MS),
      );
    },
    [dismiss],
  );

  useEffect(() => {
    const t = timers.current;
    return () => t.forEach(clearTimeout);
  }, []);

  const value = useMemo(() => show, [show]);
  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="toast-region" role="status" aria-live="polite">
        {items.map((t) => (
          <div key={t.id} className={`toast ${t.kind}`}>
            <span>{t.message}</span>
            {t.action && (
              <button type="button" className="btn btn-secondary" onClick={t.action.onClick}>
                {t.action.label}
              </button>
            )}
            <button
              type="button"
              className="btn btn-ghost btn-icon"
              aria-label={vi.common.close}
              style={{ color: "inherit", marginLeft: "auto" }}
              onClick={() => dismiss(t.id)}
            >
              ✕
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): Show {
  const show = useContext(ToastContext);
  if (!show) throw new Error("useToast must be used inside <ToastProvider>");
  return show;
}
