import { screen, waitFor } from "@testing-library/react";
import { nav } from "../api-client/http";
import { axeViolations, ME, mockFetch, renderApp } from "../test/utils";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("US-101 login", () => {
  it("signed-in user lands on the workspace and sees their name and role (AC-101.1)", async () => {
    mockFetch((url) => {
      if (url === "/api/v1/me") return { status: 200, body: ME };
      if (url.startsWith("/api/v1/documents")) return { status: 200, body: { items: [], nextCursor: null } };
    });
    renderApp("/");
    expect(await screen.findByText("Trần Thu Hà")).toBeInTheDocument();
    expect(screen.getByText("Thành viên BD")).toBeInTheDocument();
  });

  it("no session → redirect to the IdP login keeping the current path", async () => {
    const assign = vi.spyOn(nav, "assign").mockImplementation(() => undefined);
    mockFetch(() => ({ status: 401, body: { code: "AUTH_REQUIRED" } }));
    renderApp("/");
    await waitFor(() => expect(assign).toHaveBeenCalledWith(expect.stringMatching(/^\/auth\/login\?returnTo=/)));
    expect(screen.queryByText("Kho tài liệu")).not.toBeInTheDocument();
  });

  it("login page links to /auth/login and passes axe", async () => {
    const { container } = renderApp("/login?returnTo=/abc");
    expect(screen.getByRole("link", { name: "Đăng nhập bằng tài khoản công ty" })).toHaveAttribute(
      "href",
      "/auth/login?returnTo=%2Fabc",
    );
    expect(await axeViolations(container)).toEqual([]);
  });

  it("refuses an absolute returnTo (open redirect)", () => {
    renderApp("/login?returnTo=https://evil.example");
    expect(screen.getByRole("link", { name: "Đăng nhập bằng tài khoản công ty" })).toHaveAttribute(
      "href",
      "/auth/login?returnTo=%2F",
    );
  });

  it("IdP down → 'Chưa đăng nhập được' with a retry button (AC-101.3)", () => {
    renderApp("/login?error=idp");
    expect(screen.getByRole("heading", { name: "Chưa đăng nhập được" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Thử lại" })).toHaveAttribute("href", "/auth/login?returnTo=%2F");
  });
});

describe("US-102 denied", () => {
  it("shows the denial message and calls no API (AC-102.1)", async () => {
    const calls = mockFetch(() => ({ status: 200, body: {} }));
    const { container } = renderApp("/denied");
    expect(screen.getByText("Bạn chưa được cấp quyền dùng công cụ này. Liên hệ trưởng nhóm BD.")).toBeInTheDocument();
    expect(calls).toHaveLength(0);
    expect(await axeViolations(container)).toEqual([]);
  });

  it("a FORBIDDEN_ROLE answer from /me lands on /denied", async () => {
    mockFetch(() => ({ status: 403, body: { code: "FORBIDDEN_ROLE" } }));
    renderApp("/");
    expect(
      await screen.findByRole("heading", { name: "Bạn chưa được cấp quyền dùng công cụ này" }),
    ).toBeInTheDocument();
  });
});
