# AI Trading — Antigravity Team Policy

Repository: giakhagroup/ai-trading
Branch context: release/1.0.0

This is financial/trading software. Correctness, deterministic behavior,
reproducibility, market-data integrity, and security take priority over speed.

## Agent hierarchy
ORCHESTRATOR -> ARCHITECT -> QUANT/PROVIDER-POC/SECURITY -> CODER -> TESTER -> REVIEWER

## Model policy
Use one Google account. Agents select only a model tier:
- pro = strategic/reasoning-heavy work
- flash = fast/repetitive validation

Policy:
- orchestrator: pro
- architect: pro
- quant: pro
- provider-poc: pro
- coder: pro
- tester: flash
- reviewer: pro
- security: pro

The exact model version is resolved by Antigravity's available model catalog.
Never put API keys or Google credentials in agent files.

## Mandatory workflow
1. Read requirements and relevant repository code.
2. ARCHITECT produces the plan.
3. QUANT reviews trading/market-data changes.
4. PROVIDER-POC reviews uncertain TradingView/provider behavior.
5. SECURITY reviews security-sensitive changes.
6. CODER implements approved scope.
7. TESTER independently validates.
8. REVIEWER independently reviews the final diff.
9. Any BLOCKED / FAIL / CHANGES_REQUIRED result must be resolved before DONE.

## No-go rules
Never introduce look-ahead bias, future data, data leakage, candle-timing errors,
non-deterministic backtests, hard-coded credentials, unsupported provider claims,
or unrelated refactors. Never weaken/delete tests to make them pass.

## Definition of done
Implementation matches approved scope; required tests and specialist gates pass;
final reviewer approves; remaining risks are documented.
