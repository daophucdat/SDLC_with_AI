# REL-02 · Diễn tập sao lưu và khôi phục

| Thuộc tính | Giá trị |
|---|---|
| Loại | Phát hành |
| Sprint | Sprint 5 (11/01 → 15/01/2027) |
| Vai trò thực hiện | DevOps |
| Phụ thuộc | EN-02 |
| Trạng thái | To Do |
| Người nhận | `[TBD]` |

## 1. Mục tiêu

Chứng minh khôi phục được hệ thống trong ≤ 1 ngày làm việc (REL-02) và mất tối đa 24 giờ dữ liệu (REL-03), trước khi đưa dữ liệu thật vào.

## 2. Công việc chi tiết

- [ ] Ghi lại trạng thái staging: số tài liệu, số đoạn, một câu hỏi mẫu kèm câu trả lời và trích dẫn.
- [ ] Khôi phục CSDL về một thời điểm (PITR) vào một môi trường riêng.
- [ ] Khôi phục object storage (versioning) tương ứng.
- [ ] Dựng lại `api`, `worker`, `embedder` bằng IaC; ghi lại thời gian từng bước.
- [ ] So sánh số liệu với trạng thái đã ghi; chạy lại câu hỏi mẫu.
- [ ] Viết runbook `docs/implement/reports/restore_runbook.md` và biên bản diễn tập.

## 3. Tiêu chí nghiệm thu

- [ ] Tổng thời gian khôi phục ≤ 4 giờ (mục tiêu SAD §4.2); RPO đo được ≤ 24 giờ.
- [ ] Câu hỏi mẫu cho kết quả giống trước khi khôi phục (cùng tài liệu và trang được trích dẫn).
- [ ] Runbook đủ để một người không tham gia diễn tập làm theo được.

---

*Nguồn: [implement_plan.md](../implement_plan.md) §4 (Sprint 5), §7.2, §9.*
