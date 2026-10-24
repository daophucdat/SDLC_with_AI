# REL-01 · Kiểm tra toàn bộ điều kiện ra mắt LG-01 → LG-17

| Thuộc tính | Giá trị |
|---|---|
| Loại | Phát hành |
| Sprint | Sprint 5 (11/01 → 15/01/2027) |
| Vai trò thực hiện | QA, Tech lead |
| Phụ thuộc | Tất cả story P0 / P1 và enabler |
| Trạng thái | To Do |
| Người nhận | `[TBD]` |

## 1. Mục tiêu

Chứng minh bằng bằng chứng rằng 17 điều kiện ra mắt (PRD §5.1, [implement_plan.md §7.2](../implement_plan.md)) đều đạt, làm đầu vào cho họp Go / No-go (REL-03).

## 2. Công việc chi tiết

- [ ] Tạo `docs/implement/reports/launch_gates.md`: một dòng cho mỗi LG, gồm kết quả, ngưỡng, bằng chứng (link báo cáo CI, ảnh chụp dashboard, biên bản), người xác nhận.
- [ ] LG-01, LG-13: xuất báo cáo E2E (EN-12); đối chiếu mọi AC P0 / P1 có test và đều pass.
- [ ] LG-02: lọc bug tracker, 0 lỗi Critical / High đang mở.
- [ ] LG-03, LG-04: Trưởng nhóm BD chấm kết quả EN-10 / US-402 trên bộ câu hỏi kiểm thử cuối cùng.
- [ ] LG-05: QA kiểm tay mẫu 30 trích dẫn ngẫu nhiên.
- [ ] LG-06, LG-08: chạy k6 (100 câu hỏi) và Lighthouse trên staging có cấu hình như prod.
- [ ] LG-07: chạy lại test file 300 trang / 50 MB.
- [ ] LG-09, LG-11, LG-12: nhận văn bản phê duyệt của IT / Bảo mật và điều khoản của nhà cung cấp AI.
- [ ] LG-10: chạy bộ test truy cập trái phép.
- [ ] LG-14: E2E trên trình duyệt chuẩn của công ty.
- [ ] LG-15: kiểm tra 13 sự kiện có dữ liệu trên staging.
- [ ] LG-16: nhận kết quả đo hiện trạng M-001 từ Trưởng nhóm BD.
- [ ] LG-17: kích hoạt thử cảnh báo gián đoạn, xác nhận đội vận hành nhận được.

## 3. Tiêu chí nghiệm thu

- [ ] `launch_gates.md` có đủ 17 dòng, mỗi dòng có bằng chứng và người xác nhận.
- [ ] Mọi LG chưa đạt đều có kế hoạch xử lý và ngày hoàn thành, hoặc được ghi là lý do No-go.

---

*Nguồn: [implement_plan.md](../implement_plan.md) §4 (Sprint 5), §7.2, §9.*
