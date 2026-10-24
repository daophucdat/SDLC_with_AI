# EN-11 · Design system thành code

| Thuộc tính | Giá trị |
|---|---|
| Loại | Enabler · EN. Enabler kỹ thuật |
| Sprint | Sprint 0 ([implement_plan.md §4](../implement_plan.md)) |
| Ưu tiên | Enabler (bắt buộc cho các story phụ thuộc) |
| Story point | 5 `[Đề xuất]` |
| Vai trò thực hiện | Frontend, QA |
| Phụ thuộc | EN-01 |
| Chặn bởi | — |
| Trạng thái | To Do |
| Người nhận | `[TBD]` |

## 1. Mục tiêu

Chuyển token (`tokens.css`) và component của [design-system.html](../04-design/UI_UX_design/design-system.html) sang React

**Truy vết:** Blueprint §3.6, UX-S05

**Thiết kế giao diện:** [`design-system.html`](../../04-design/UI_UX_design/design-system.html)

## 2. Phạm vi

**Trong phạm vi:** các công việc ở mục 4.

**Ngoài phạm vi:** Những gì không được liệt kê ở mục 4 và mục 6.

## 3. Hợp đồng liên quan

Nguồn đầy đủ: [dev_tasks.md — Phần 0](../dev_tasks.md). Đổi hợp đồng thì sửa ở đó trước.

Task này không đổi hợp đồng chung; dùng quy ước ở dev_tasks.md §0.1.

## 4. Công việc chi tiết

- [ ] **T-EN11.1** `FE` — **Token**: Copy `docs/04-design/UI_UX_design/assets/tokens.css` → `web/src/ui/tokens.css`; stylelint chặn mã màu viết trực tiếp ngoài file này
- [ ] **T-EN11.2** `FE` — **Component cơ bản**: `Button` (primary / secondary / ghost / danger, size lg, icon), `Badge` (ready / processing / warning / error / neutral), `Input`, `Textarea`, `Select`, `Chip`, `Spinner`, `ProgressBar`
- [ ] **T-EN11.3** `FE` — **Component phản hồi**: `Toast` + `useToast` (role=status, tự ẩn 5 s), `GlobalBanner`, `EmptyState`, `ConfirmDialog` (focus trap, focus mặc định ở Huỷ, Esc để đóng, `role="alertdialog"`)
- [ ] **T-EN11.4** `FE` — **Bố cục**: `AppShell` 3 vùng + responsive theo UX-S04 (≥ 1280 / 1024–1279 / < 1024)
- [ ] **T-EN11.5** `QA` — **Kiểm tra**: Storybook hoặc trang `/__ui` (chỉ ở dev) hiển thị mọi trạng thái như [design-system.html](../04-design/UI_UX_design/design-system.html); test axe cho từng component

## 5. Trường hợp biên và lưu ý

- Xem các trường hợp lỗi ở mục 3 (mã lỗi) và các tiêu chí nghiệm thu ở mục 6.

## 6. Tiêu chí nghiệm thu

- [ ] Component dùng lại được ở mọi màn hình; lint CSS chặn mã màu viết trực tiếp

## 7. Kiểm thử

| Test | Loại | Ánh xạ |
|---|---|---|
| Kiểm chứng tiêu chí hoàn thành ở mục 6 | Integration / báo cáo | EN-11 |

## 8. Definition of Done

- [ ] Mọi tiêu chí nghiệm thu ở mục 6 đạt, có test tự động chạy trong CI.
- [ ] Code đã được review; CI xanh (lint, quy tắc import DR-1 → DR-5, unit, integration).
- [ ] Không ghi nội dung câu hỏi / câu trả lời / tài liệu vào log, span hay sự kiện (QAS-06).
- [ ] Mọi tham số lấy từ cấu hình (§0.2 của dev_tasks.md), không hard-code.
- [ ] Nếu có giao diện: đúng prototype, dùng design token, axe không có lỗi serious / critical.
- [ ] Đã deploy lên staging và PO / BA nghiệm thu bằng demo.

---

*Sinh từ [userStory.md](../userStory.md) và [dev_tasks.md](../dev_tasks.md). Khi hai tài liệu nguồn thay đổi, cập nhật file này cho khớp.*
