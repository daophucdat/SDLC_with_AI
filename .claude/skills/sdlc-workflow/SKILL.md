---
name: sdlc-workflow
description: >-
  Điều phối cả vòng SDLC từ tài liệu BRD: phân tích → thiết kế → lập kế hoạch → phát triển → kiểm thử → phát hành,
  mỗi pha kết thúc ở cổng phê duyệt của con người; trạng thái lưu trong docs/sdlc-state.md để phiên sau chạy
  tiếp. Dùng khi người dùng muốn chạy toàn bộ quy trình, "từ BRD tới code và test", tiếp tục workflow, chạy pha kế.
argument-hint: "<đường dẫn BRD> | tiếp | pha <số>"
disable-model-invocation: true
---

Workflow SDLC cho **$ARGUMENTS**. Một prompt khởi động; agent làm, **người duyệt ở cuối mỗi pha**.

## KHÔNG ĐƯỢC (đọc trước mọi thứ — compaction cắt từ cuối file)
- **Không sang pha kế khi chưa có câu "duyệt" rõ ràng của người dùng cho pha hiện tại.** Im lặng, "ok để xem", câu hỏi → không phải duyệt.
- Không sửa artefact của pha đã duyệt nếu không có yêu cầu thay đổi; khi phải sửa → mở lại cổng pha đó.
- Không đoán phạm vi: thiếu thông tin trong BRD → câu hỏi mở ở cổng, không bịa yêu cầu.
- Không push, không merge, không deploy. Commit chỉ qua `/commit-gate` (người gọi).
- Không bỏ cổng chất lượng của pha (test đỏ trước, `dev.sh check`, 2 lượt chạy TC) để kịp tiến độ.

## Trạng thái hiện tại
!`sed -n '1,40p' docs/sdlc-state.md 2>/dev/null || echo "chưa có docs/sdlc-state.md — bắt đầu ở pha 0"`

## Vòng lặp mỗi pha
1. Đọc `docs/sdlc-state.md`: pha hiện tại, quyết định đã duyệt, yêu cầu thay đổi đang mở.
2. Làm pha đó theo [phases.md](phases.md): đầu vào → việc → artefact → checklist "xong".
3. Tự kiểm checklist; thiếu → làm tiếp, không trình cổng.
4. **Trình cổng** (rồi dừng lượt): artefact (đường dẫn), 3–7 quyết định chính, câu hỏi mở, rủi ro, checklist đã tick, đề xuất pha kế. Kết thúc bằng: *"Trả lời **duyệt** để sang pha N+1, hoặc nêu thay đổi."*
5. Người dùng trả lời → ghi vào `docs/sdlc-state.md` (ngày, pha, quyết định / thay đổi). Duyệt → pha kế; thay đổi → sửa và trình lại cổng đó.

Pha 4 (phát triển) lặp theo từng story trong backlog đã duyệt; mỗi story là một cổng nhỏ. Pha có nhiều việc độc lập (nhiều story không phụ thuộc) có thể giao subagent song song — kết quả vẫn qua cổng.
