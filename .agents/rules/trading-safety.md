# Trading Safety — Always On

Apply to trading, market-data, strategy, signal, risk, scanner, MTF, and backtest changes.

1. No look-ahead bias.
2. No future candle/data access.
3. Decisions use only information available at the decision timestamp.
4. Explicitly distinguish forming and closed candles.
5. Preserve timezone/session semantics.
6. Backtests must be deterministic and reproducible.
7. Never silently change historical-data assumptions or signal timing.
8. Never confuse a score with a probability.
9. Never treat a mock provider as equivalent to a production provider.

MTF: higher-timeframe information must only become available when it is actually
available under the strategy's defined candle semantics.

Signal lifecycle:
candidate signal -> validated signal -> execution decision -> risk decision.

If correctness cannot be established, BLOCK and request a Quant decision.
