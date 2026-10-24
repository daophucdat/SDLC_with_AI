// /__ui (dev only, EN-11 T-EN11.5): every component state, like design-system.html.
import { useState } from "react";
import { vi } from "../i18n/vi";
import {
  Badge,
  Button,
  Chip,
  ConfirmDialog,
  EmptyState,
  GlobalBanner,
  Input,
  ProgressBar,
  Select,
  Spinner,
  Textarea,
  useToast,
} from "../ui";

export function UiGallery() {
  const toast = useToast();
  const [dialog, setDialog] = useState(false);
  const [chip, setChip] = useState(false);
  return (
    <main className="doc-page" style={{ padding: "var(--space-6)", display: "grid", gap: "var(--space-6)" }}>
      <h1>Design system — component gallery</h1>
      <section className="row" aria-label="Buttons">
        <Button variant="primary">Primary</Button>
        <Button>Secondary</Button>
        <Button variant="ghost">Ghost</Button>
        <Button variant="danger">Danger</Button>
        <Button variant="primary" size="lg">
          Large
        </Button>
        <Button variant="ghost" icon aria-label="Icon button">
          ⋯
        </Button>
        <Button disabled>Disabled</Button>
      </section>
      <section className="row" aria-label="Badges">
        <Badge tone="ready">{vi.status.READY}</Badge>
        <Badge tone="processing">{vi.status.PROCESSING}</Badge>
        <Badge tone="warning">{vi.status.NO_TEXT}</Badge>
        <Badge tone="error">{vi.status.ERROR}</Badge>
        <Badge tone="neutral">Neutral</Badge>
      </section>
      <section style={{ display: "grid", gap: "var(--space-3)", maxWidth: 420 }} aria-label="Fields">
        <label className="field">
          Input
          <Input placeholder="Placeholder" />
        </label>
        <label className="field">
          Textarea
          <Textarea rows={3} />
        </label>
        <label className="field">
          Select
          <Select>
            <option>Một</option>
            <option>Hai</option>
          </Select>
        </label>
        <Chip pressed={chip} onClick={() => setChip((c) => !c)}>
          Chip
        </Chip>
        <Spinner label="Đang tải" />
        <ProgressBar value={42} label="Tiến độ mẫu" />
      </section>
      <section style={{ display: "grid", gap: "var(--space-2)" }} aria-label="Feedback">
        <GlobalBanner tone="info">Info banner</GlobalBanner>
        <GlobalBanner tone="warning">{vi.banners.offline}</GlobalBanner>
        <GlobalBanner tone="error">Error banner</GlobalBanner>
        <EmptyState icon="📂" title={vi.library.emptyTitle} headingLevel={2}>
          {vi.library.emptyBody}
        </EmptyState>
        <div className="row">
          <Button onClick={() => toast("Thông báo mẫu")}>Toast</Button>
          <Button onClick={() => toast("Đã sẵn sàng", "success")}>Toast success</Button>
          <Button onClick={() => toast(vi.errors.INTERNAL, "error")}>Toast error</Button>
          <Button variant="danger" onClick={() => setDialog(true)}>
            ConfirmDialog
          </Button>
        </div>
      </section>
      <ConfirmDialog
        open={dialog}
        title="Gỡ tài liệu?"
        body="Tài liệu sẽ không còn được dùng cho câu trả lời mới của cả đội."
        confirmLabel="Gỡ tài liệu"
        onConfirm={() => setDialog(false)}
        onCancel={() => setDialog(false)}
      />
    </main>
  );
}
