# Mẫu một bảng test case (docs/test-cases.md)

```markdown
## US-xxx · <tên story>

Tiền điều kiện thêm: <dữ liệu / trạng thái cần có trước, nếu khác tiền điều kiện chung>.

| TC | AC | H | Bước | PASS khi (ghi trước) | FAIL khi |
|---|---|---|---|---|---|
| TC-xxx-01 | AC-xxx.1 | H | <hành động + dữ liệu cụ thể> | <kết quả quan sát được, có số / chuỗi chính xác> | <điều ngược lại cụ thể> |
```

Ma trận cuối file:

```markdown
| AC | TC | Số TC | Heuristic phủ |
|---|---|---|---|
| AC-xxx.1 | TC-xxx-01, 02 | 2 | H, B |
```

Kiểm tra trước khi xong:
- [ ] Mọi AC của story có ≥ 1 TC; mọi TC trỏ về đúng 1 AC.
- [ ] Cột "PASS khi" có số, chuỗi giao diện chính xác (lấy từ `web/src/i18n/vi.ts`) hoặc trạng thái API — không có tính từ.
- [ ] Dữ liệu test có tên riêng, không trùng TC khác.
- [ ] TC thủ công ghi rõ lý do và môi trường.
