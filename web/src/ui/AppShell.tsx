// AppShell (EN-11 T-EN11.4): header + banners + 3-region body. Breakpoints (≥1280 / 1024–1279 / <1024) are
// in components.css (UX-S04); below 1280 px the library collapses to a rail opened by the ☰ toggle.
import type { ReactNode } from "react";
import { NavLink } from "react-router-dom";
import type { MeDto } from "../api-client/types";
import { vi } from "../i18n/vi";
import { Button } from "./primitives";

function initials(name: string): string {
  const parts = name.trim().split(/\s+/);
  return ((parts[0]?.[0] ?? "") + (parts.length > 1 ? parts[parts.length - 1][0] : "")).toUpperCase();
}

export interface AppShellProps {
  me: MeDto;
  banners?: ReactNode;
  library?: ReactNode;
  libraryOpen?: boolean;
  onToggleLibrary?: () => void;
  source?: ReactNode;
  onLogout: () => void;
  children: ReactNode;
}

export function AppShell({
  me,
  banners,
  library,
  libraryOpen = false,
  onToggleLibrary,
  source,
  onLogout,
  children,
}: AppShellProps) {
  const canSeeMetrics = me.permissions.includes("metrics:view");
  return (
    <div className="workspace">
      <a className="skip-link" href="#main">
        Chuyển tới nội dung chính
      </a>
      <header className="app-header">
        {library && (
          <Button
            variant="ghost"
            icon
            className="rail-toggle"
            aria-label="Mở kho tài liệu"
            aria-expanded={libraryOpen}
            aria-controls="library"
            onClick={onToggleLibrary}
          >
            ☰
          </Button>
        )}
        <a className="brand" href="/">
          <span className="brand-mark" aria-hidden="true">
            C
          </span>
          {vi.appName}
        </a>
        <nav className="app-nav" aria-label="Điều hướng chính">
          <NavLink to="/" end>
            Hỏi đáp
          </NavLink>
          {canSeeMetrics && <NavLink to="/metrics">Số liệu</NavLink>}
        </nav>
        <div className="user-menu">
          <span className="muted">{vi.roles[me.role] ?? me.role}</span>
          <span className="avatar" aria-hidden="true">
            {initials(me.displayName)}
          </span>
          <span>{me.displayName}</span>
          <Button variant="ghost" onClick={onLogout}>
            {vi.common.logout}
          </Button>
        </div>
      </header>
      {banners}
      <div className={`ws-body${source ? " source-open" : ""}`}>
        {library}
        <main className="chat" id="main">
          {children}
        </main>
        {source}
      </div>
    </div>
  );
}
