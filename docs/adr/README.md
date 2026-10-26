# Architecture Decision Records

ADR-01 → ADR-12 nằm trong [SAD §1.3](../03-design/SAD.md). Các ADR dưới đây ghi lại quyết định phát sinh **trong lúc hiện thực** (Day 5: "Ghi ADR cho quyết định kiến trúc mới"). Mỗi ADR mới: copy mẫu cuối trang, đánh số tiếp, thêm một dòng vào bảng, và nhắc mã ADR trong commit.

| ADR | Quyết định | Trạng thái | Story |
|---|---|---|---|
| [ADR-13](ADR-13-two-phase-ask.md) | Hỏi đáp chia 2 pha: kiểm tra (lỗi HTTP) rồi mới mở luồng SSE | Accepted | US-301, EN-06 |
| [ADR-14](ADR-14-purge-all-object-versions.md) | Gỡ tài liệu xoá mọi phiên bản object; khôi phục phải áp lại lần gỡ | Accepted | US-204, REL-02 |
| [ADR-15](ADR-15-oidc-backchannel.md) | URL IdP nội bộ cho lời gọi server-to-server | Accepted | US-101, EN-02 |
| [ADR-16](ADR-16-done-first-token-ms.md) | Thêm `firstTokenMs` vào sự kiện SSE `done` | Accepted | US-306, EN-12 |
| [ADR-17](ADR-17-kill-switch-flag.md) | Cờ `qa_off` tắt hỏi đáp không cần deploy | Accepted | REL-03 |
| [ADR-18](ADR-18-llm-provider-defaults.md) | Cấu hình mặc định của LLM và adapter giả lập | Accepted | EN-06 |
| [ADR-19](ADR-19-quality-gates.md) | Ngưỡng cổng chất lượng L0 | Accepted | EN-01 |

## Mẫu

```markdown
# ADR-NN: <quyết định>
- Trạng thái: Proposed | Accepted | Superseded by ADR-xx
- Ngày: YYYY-MM-DD · Story: US-xxx / EN-xx
## Bối cảnh
## Quyết định
## Hệ quả (tốt / xấu / phải làm thêm)
## Phương án đã cân nhắc
```
