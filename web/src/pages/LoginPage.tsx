// Login (US-101) — states as login.html: default, ?error=idp (IdP not responding), ?error=state (expired attempt).
// /denied (US-102 T102.4) calls no API at all, so nothing about the library leaks to a non-BD account.
import { useSearchParams } from "react-router-dom";
import { vi } from "../i18n/vi";

function loginHref(returnTo: string | null): string {
  return `/auth/login?returnTo=${encodeURIComponent(returnTo && returnTo.startsWith("/") ? returnTo : "/")}`;
}

export function LoginPage() {
  const [params] = useSearchParams();
  const error = params.get("error");
  const href = loginHref(params.get("returnTo"));

  if (error) {
    return (
      <main className="login-shell">
        <section className="card login-card" aria-labelledby="error-title">
          <div className="empty-icon" aria-hidden="true">
            ⚠️
          </div>
          <h1 id="error-title">Chưa đăng nhập được</h1>
          <p className="muted">
            {error === "idp"
              ? "Hệ thống tài khoản của công ty đang không phản hồi. Vui lòng thử lại sau ít phút."
              : "Phiên đăng nhập đã quá hạn hoặc không hợp lệ. Vui lòng đăng nhập lại."}
          </p>
          <a className="btn btn-primary" href={href}>
            Thử lại
          </a>
        </section>
      </main>
    );
  }

  return (
    <main className="login-shell">
      <section className="card login-card" aria-labelledby="login-title">
        <div className="brand-mark" aria-hidden="true">
          C
        </div>
        <h1 id="login-title">{vi.appName}</h1>
        <p className="muted">
          Hỏi đáp trên toàn bộ tài liệu PDF của đội phát triển kinh doanh. Mỗi câu trả lời đều ghi rõ tài liệu và trang
          nguồn.
        </p>
        <a className="btn btn-primary btn-lg" href={href} style={{ width: "100%", marginTop: "var(--space-4)" }}>
          Đăng nhập bằng tài khoản công ty
        </a>
        <p className="xs muted" style={{ marginTop: "var(--space-4)" }}>
          Chỉ thành viên đội BD đã được cấp quyền mới truy cập được. Bạn sẽ được chuyển tới trang đăng nhập của công ty.
        </p>
      </section>
    </main>
  );
}

export function DeniedPage() {
  return (
    <main className="login-shell">
      <section className="card login-card" aria-labelledby="denied-title">
        <div className="empty-icon" aria-hidden="true">
          🔒
        </div>
        <h1 id="denied-title">Bạn chưa được cấp quyền dùng công cụ này</h1>
        <p className="muted">{vi.errors.FORBIDDEN_ROLE}</p>
        <div className="row" style={{ justifyContent: "center", marginTop: "var(--space-4)" }}>
          <a className="btn btn-secondary" href="/login">
            Đăng nhập bằng tài khoản khác
          </a>
        </div>
      </section>
    </main>
  );
}
