import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Route, Routes } from "react-router-dom";
import { ApiError } from "./api-client/http";
import { RequireAuth } from "./auth/RequireAuth";
import { MetricsPage } from "./metrics/MetricsPage";
import { DeniedPage, LoginPage } from "./pages/LoginPage";
import { UiGallery } from "./pages/UiGallery";
import { WorkspacePage } from "./pages/WorkspacePage";
import { ToastProvider } from "./ui";

export function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        // 4xx are answers, not glitches: retry only network / 5xx, at most twice
        retry: (n, err) => n < 2 && !(err instanceof ApiError && err.status >= 400 && err.status < 500),
        refetchOnWindowFocus: true,
      },
    },
  });
}

export function App({ client = makeQueryClient() }: { client?: QueryClient }) {
  return (
    <QueryClientProvider client={client}>
      <ToastProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/denied" element={<DeniedPage />} />
          {import.meta.env.DEV && <Route path="/__ui" element={<UiGallery />} />}
          <Route
            path="/metrics"
            element={
              <RequireAuth>
                <MetricsPage />
              </RequireAuth>
            }
          />
          <Route
            path="*"
            element={
              <RequireAuth>
                <WorkspacePage />
              </RequireAuth>
            }
          />
        </Routes>
      </ToastProvider>
    </QueryClientProvider>
  );
}
