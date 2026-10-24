// GlobalBanner + EmptyState (EN-11 T-EN11.3)
import type { ReactNode } from "react";

export function GlobalBanner({
  tone,
  children,
  action,
}: {
  tone: "info" | "warning" | "error";
  children: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className={`banner banner-${tone}`} role={tone === "error" ? "alert" : "status"}>
      <span>{children}</span>
      {action}
    </div>
  );
}

export function EmptyState({
  icon,
  title,
  children,
  headingLevel = 3,
}: {
  icon: string;
  title: string;
  children?: ReactNode;
  headingLevel?: 2 | 3;
}) {
  const H = headingLevel === 2 ? "h2" : "h3";
  return (
    <div className="empty">
      <div className="empty-icon" aria-hidden="true">
        {icon}
      </div>
      <H>{title}</H>
      {children && <p>{children}</p>}
    </div>
  );
}
