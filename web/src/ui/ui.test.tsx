import { act, fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { UiGallery } from "../pages/UiGallery";
import { axeViolations, renderInRouter } from "../test/utils";
import { ConfirmDialog } from "./ConfirmDialog";
import { TOAST_MS, ToastProvider, useToast } from "./Toast";
import { AppShell, Badge, Button, ProgressBar } from ".";
import { ME } from "../test/utils";

function DialogHarness({ onConfirm = () => undefined }: { onConfirm?: () => void }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <Button onClick={() => setOpen(true)}>Mở</Button>
      <ConfirmDialog
        open={open}
        title="Gỡ tài liệu?"
        body="Không hoàn tác được."
        confirmLabel="Gỡ tài liệu"
        onConfirm={() => {
          onConfirm();
          setOpen(false);
        }}
        onCancel={() => setOpen(false)}
      />
    </>
  );
}

describe("ConfirmDialog", () => {
  it("is an alertdialog, focuses Cancel, traps Tab, closes on Esc and restores focus", async () => {
    const user = userEvent.setup();
    render(<DialogHarness />);
    const opener = screen.getByRole("button", { name: "Mở" });
    await user.click(opener);

    const dialog = screen.getByRole("alertdialog", { name: "Gỡ tài liệu?" });
    expect(dialog).toHaveAccessibleDescription("Không hoàn tác được.");
    expect(screen.getByRole("button", { name: "Huỷ" })).toHaveFocus();

    await user.tab();
    expect(screen.getByRole("button", { name: "Gỡ tài liệu" })).toHaveFocus();
    await user.tab();
    expect(screen.getByRole("button", { name: "Huỷ" })).toHaveFocus();
    await user.tab({ shift: true });
    expect(screen.getByRole("button", { name: "Gỡ tài liệu" })).toHaveFocus();

    await user.keyboard("{Escape}");
    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
    expect(opener).toHaveFocus();
  });

  it("runs onConfirm", async () => {
    const onConfirm = vi.fn();
    render(<DialogHarness onConfirm={onConfirm} />);
    fireEvent.click(screen.getByRole("button", { name: "Mở" }));
    fireEvent.click(screen.getByRole("button", { name: "Gỡ tài liệu" }));
    expect(onConfirm).toHaveBeenCalledOnce();
  });
});

describe("Toast", () => {
  it("announces in a status region and hides after 5 s", () => {
    vi.useFakeTimers();
    function Fire() {
      const toast = useToast();
      return <button onClick={() => toast("Đã lưu", "success")}>fire</button>;
    }
    render(
      <ToastProvider>
        <Fire />
      </ToastProvider>,
    );
    fireEvent.click(screen.getByText("fire"));
    expect(screen.getByRole("status")).toHaveTextContent("Đã lưu");
    act(() => void vi.advanceTimersByTime(TOAST_MS + 1));
    expect(screen.getByRole("status")).not.toHaveTextContent("Đã lưu");
    vi.useRealTimers();
  });

  it("can be closed by hand", () => {
    function Fire() {
      const toast = useToast();
      return <button onClick={() => toast("Xin chào")}>fire</button>;
    }
    render(
      <ToastProvider>
        <Fire />
      </ToastProvider>,
    );
    fireEvent.click(screen.getByText("fire"));
    fireEvent.click(screen.getByRole("button", { name: "Đóng thông báo" }));
    expect(screen.queryByText("Xin chào")).not.toBeInTheDocument();
  });
});

describe("primitives", () => {
  it("map variants to the prototype classes", () => {
    render(
      <>
        <Button variant="danger" size="lg">
          X
        </Button>
        <Badge tone="ready">Sẵn sàng</Badge>
        <ProgressBar value={142} label="Tiến độ" />
      </>,
    );
    expect(screen.getByRole("button", { name: "X" })).toHaveClass("btn", "btn-danger", "btn-lg");
    expect(screen.getByText("Sẵn sàng")).toHaveClass("badge", "badge-ready");
    expect(screen.getByRole("progressbar", { name: "Tiến độ" })).toHaveAttribute("aria-valuenow", "100");
  });

  it("AppShell shows name and role, hides Số liệu from members", () => {
    renderInRouter(
      <AppShell me={ME} onLogout={() => undefined}>
        nội dung
      </AppShell>,
    );
    expect(screen.getByText("Trần Thu Hà")).toBeInTheDocument();
    expect(screen.getByText("Thành viên BD")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Số liệu" })).not.toBeInTheDocument();
  });

  it("AppShell shows Số liệu with metrics:view", () => {
    renderInRouter(
      <AppShell me={{ ...ME, role: "BD_LEAD", permissions: ["metrics:view"] }} onLogout={() => undefined}>
        x
      </AppShell>,
    );
    expect(screen.getByRole("link", { name: "Số liệu" })).toBeInTheDocument();
    expect(screen.getByText("Trưởng nhóm BD")).toBeInTheDocument();
  });
});

describe("accessibility (axe)", () => {
  it("component gallery has no violations", async () => {
    const { container } = render(
      <ToastProvider>
        <UiGallery />
      </ToastProvider>,
    );
    expect(await axeViolations(container)).toEqual([]);
  });

  it("open dialog has no violations", async () => {
    const { container } = render(<DialogHarness />);
    fireEvent.click(screen.getByRole("button", { name: "Mở" }));
    expect(await axeViolations(container)).toEqual([]);
  });
});
