# EN-03 · Dịch vụ embedder + benchmark

| Thuộc tính | Giá trị |
|---|---|
| Loại | Enabler · EN. Enabler kỹ thuật |
| Sprint | Sprint 0 ([implement_plan.md §4](../implement_plan.md)) |
| Ưu tiên | Enabler (bắt buộc cho các story phụ thuộc) |
| Story point | 5 `[Đề xuất]` |
| Vai trò thực hiện | AI engineer, Backend |
| Phụ thuộc | EN-02 |
| Chặn bởi | — |
| Trạng thái | To Do |
| Người nhận | `[TBD]` |

## 1. Mục tiêu

Container BGE-M3 (CPU); đo tốc độ lập chỉ mục và độ trễ truy vấn

**Truy vết:** ADR-08, **TQ-02**, NFR-03

## 2. Phạm vi

**Trong phạm vi:** các công việc ở mục 4.

**Ngoài phạm vi:** Những gì không được liệt kê ở mục 4 và mục 6.

## 3. Hợp đồng liên quan

Nguồn đầy đủ: [dev_tasks.md — Phần 0](../dev_tasks.md). Đổi hợp đồng thì sửa ở đó trước.

**Cấu hình**

| Biến | Mặc định |
|---|---|
| `EMBEDDER_URL`, `EMBED_DIM`, `EMBED_BATCH` | —, `1024`, `32` |

## 4. Công việc chi tiết

- [ ] **T-EN03.1** `AI` — **Container embedder**: Hugging Face TEI với mô hình BGE-M3 (dense, 1024 chiều), CPU; chỉ nhận kết nối trong mạng nội bộ
- [ ] **T-EN03.2** `BE` — **Port + adapter**: `ports/embedding.py`: `class EmbeddingProvider(Protocol): async def embed(self, texts: list[str]) -> list[list[float]]`; `adapters/embedder/tei.py` (httpx, timeout 2 s, thử lại 3 lần 100 / 400 / 1600 ms); vector được chuẩn hoá L2
- [ ] **T-EN03.3** `AI` — **Script benchmark**: `eval/bench_embedder.py`: (a) 1.500 đoạn × 500 token, lô 32, đo đoạn/giây; (b) 200 câu hỏi đơn lẻ, đo p95
- [ ] **T-EN03.4** `AI` — **Báo cáo + quyết định**: `docs/implement/reports/embedder_benchmark.md`: kết quả so với NFR-03 (≤ 5 phút / 300 trang) và ≤ 200 ms p95; quyết định số bản sao / CPU / GPU (đóng TQ-02)

## 5. Trường hợp biên và lưu ý

- Xem các trường hợp lỗi ở mục 3 (mã lỗi) và các tiêu chí nghiệm thu ở mục 6.

## 6. Tiêu chí nghiệm thu

- [ ] Báo cáo benchmark: file 300 trang ≤ 5 phút; truy vấn ≤ 200 ms p95. Nếu không đạt thì có đề xuất (thêm bản sao / GPU)

## 7. Kiểm thử

| Test | Loại | Ánh xạ |
|---|---|---|
| Kiểm chứng tiêu chí hoàn thành ở mục 6 | Integration / báo cáo | EN-03 |

## 8. Definition of Done

- [ ] Mọi tiêu chí nghiệm thu ở mục 6 đạt, có test tự động chạy trong CI.
- [ ] Code đã được review; CI xanh (lint, quy tắc import DR-1 → DR-5, unit, integration).
- [ ] Không ghi nội dung câu hỏi / câu trả lời / tài liệu vào log, span hay sự kiện (QAS-06).
- [ ] Mọi tham số lấy từ cấu hình (§0.2 của dev_tasks.md), không hard-code.
- [ ] Nếu có giao diện: đúng prototype, dùng design token, axe không có lỗi serious / critical.
- [ ] Đã deploy lên staging và PO / BA nghiệm thu bằng demo.
- [ ] Báo cáo benchmark đã được review và quyết định CPU / GPU được ghi lại (đóng TQ-02).

---

*Sinh từ [userStory.md](../userStory.md) và [dev_tasks.md](../dev_tasks.md). Khi hai tài liệu nguồn thay đổi, cập nhật file này cho khớp.*
