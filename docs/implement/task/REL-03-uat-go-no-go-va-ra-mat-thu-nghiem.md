# REL-03 · UAT, Go / No-go và ra mắt thử nghiệm

| Thuộc tính | Giá trị |
|---|---|
| Loại | Phát hành |
| Sprint | Sprint 5 (11/01 → 15/01/2027) |
| Vai trò thực hiện | PO / BA, Tech lead, Trưởng nhóm BD |
| Phụ thuộc | REL-01, REL-02 |
| Trạng thái | To Do |
| Người nhận | `[TBD]` |

## 1. Mục tiêu

Đội BD nghiệm thu, quản lý quyết định Go / No-go, và ra mắt theo đợt ([implement_plan.md §9](../implement_plan.md)).

## 2. Công việc chi tiết

- [ ] UAT: 5 thành viên BD làm 6 luồng F1 → F6 trên staging với tài liệu thật (đã được IT cho phép); ghi lỗi và phản hồi.
- [ ] Đo UX-S01: ≥ 4/5 người tự tải file và nhận câu trả lời có nguồn đầu tiên trong ≤ 3 phút.
- [ ] Chuẩn bị hướng dẫn sử dụng 1 trang và buổi giới thiệu 30 phút.
- [ ] Họp Go / No-go: quản lý, IT / Bảo mật, Trưởng nhóm BD, Tech lead; đầu vào là REL-01, REL-02, kết quả UAT.
- [ ] Nếu Go: deploy prod; tuần 1 cấp quyền cho 5 người, tuần 2 cho toàn đội (30 tài khoản); kênh hỗ trợ hoạt động.
- [ ] Lên lịch theo dõi số liệu hằng tuần và buổi đánh giá MVP sau 4 tuần dùng thực tế (không tính tuần Tết).

## 3. Tiêu chí nghiệm thu

- [ ] Có biên bản Go / No-go có chữ ký hoặc xác nhận của người phê duyệt (OQ-003).
- [ ] Prod hoạt động, đợt 1 đã đăng nhập và hỏi thành công.
- [ ] Phương án tắt nhanh (feature flag / rút quyền IdP) đã được thử.

---

*Nguồn: [implement_plan.md](../implement_plan.md) §4 (Sprint 5), §7.2, §9.*
