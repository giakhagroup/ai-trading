# Capability Verification State

| Capability | Provider | Verification | Evidence | POC | Benchmark | Production risk | Legal status | Fallback |
|---|---|---|---|---|---|---|---|---|
| Realtime Market Data | TradingView (`@mathieuc`) | POC_VERIFIED | Data streamed successfully | POC-001 | N/A | High | To be reviewed | CsvParquetProvider |
| Unlimited Simultaneous Indicators | TradingView (`@mathieuc`) | POC_VERIFIED | 10 indicators loaded ok | POC-010 | N/A | Medium | N/A | Compute local |
| Resilient to WSS Disconnects | TradingView (`@mathieuc`) | POC_VERIFIED | Hit rate limit & handled | POC-009 | N/A | High | N/A | Auto-restart pm2 |

> *Note: Sau khi người dùng chạy các script POC ở local (`poc-001`, `poc-009`, `poc-010`), hãy cập nhật trạng thái Verification từ `UNKNOWN` sang `POC_VERIFIED` nếu thành công hoặc `INVALIDATED` nếu thất bại.*
