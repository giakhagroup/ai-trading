# Assumption Register

| ASM-ID | Statement | Source | Status | Validation method | Owner | Impact | Fallback |
|---|---|---|---|---|---|---|---|
| ASM-001 | Thư viện `@mathieuc/tradingview` có thể duy trì kết nối WebSocket ổn định 24h không bị đứt. | Implementation Plan | UNKNOWN | POC-001 (Chạy 24h) | Antigravity | Core realtime data sẽ bị gián đoạn. | Cơ chế Auto-Reconnect hoặc đổi account. |
| ASM-002 | Một session TradingView (Premium) có thể chịu tải số lượng lớn Indicator (ví dụ >20 indicators/chart). | Implementation Plan | UNKNOWN | POC-010 (Load Test Study) | Antigravity | Phải tách thành nhiều session, tốn tài nguyên. | Giới hạn số Indicator / Chạy tính toán local. |
| ASM-003 | Bị Rate Limit (HTTP 429) không làm chết hoàn toàn IP mà chỉ cần backoff hợp lý là mở lại. | Implementation Plan | UNKNOWN | POC-009 (Rate Limit Test) | Antigravity | Bị ban IP vĩnh viễn, hỏng toàn bộ system. | Dùng proxy pool, phân tán account. |
