// RequireAuth (US-101 T101.7): loads /me; on 401 api() has already redirected to /auth/login?returnTo=…
import { useQuery } from "@tanstack/react-query";
import { createContext, useContext } from "react";
import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { getMe } from "../api-client/documents";
import { ApiError } from "../api-client/http";
import type { MeDto } from "../api-client/types";
import { GlobalBanner, Spinner } from "../ui";
import { vi } from "../i18n/vi";

const MeContext = createContext<MeDto | null>(null);

export function useMe(): MeDto {
  const me = useContext(MeContext);
  if (!me) throw new Error("useMe must be used inside <RequireAuth>");
  return me;
}

export function RequireAuth({ children }: { children: ReactNode }) {
  const me = useQuery({ queryKey: ["me"], queryFn: getMe, retry: false, staleTime: 5 * 60_000 });

  if (me.isPending) {
    return (
      <div className="login-shell">
        <Spinner label="Đang tải" />
      </div>
    );
  }
  if (me.isError) {
    const code = me.error instanceof ApiError ? me.error.code : "INTERNAL";
    if (code === "AUTH_REQUIRED") return null; // browser is navigating to the IdP
    if (code === "FORBIDDEN_ROLE") return <Navigate to="/denied" replace />;
    return (
      <div className="login-shell">
        <GlobalBanner
          tone="error"
          action={
            <button type="button" className="btn btn-secondary" onClick={() => me.refetch()}>
              {vi.library.retry}
            </button>
          }
        >
          {vi.errors.INTERNAL}
        </GlobalBanner>
      </div>
    );
  }
  return <MeContext.Provider value={me.data}>{children}</MeContext.Provider>;
}
