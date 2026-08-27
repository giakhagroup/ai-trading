# MASTER REQUIREMENT V2.0

> **Version:** 2.0\
> **Status:** Pre-Implementation / Architecture & Feasibility Gate\
> **Supersedes:** MASTER REQUIREMENT v1.x\
> **Primary instruction:** DO NOT IMPLEMENT until discovery, capability
> verification, POC, architecture and implementation plan are approved.

## V2.0 CHANGE CONTROL

V2.0 preserves the original 120-section requirement as the baseline and
adds the V2.0 control layer below. Where an original requirement
conflicts with V2.0, **V2.0 takes precedence**. Antigravity must
explicitly report each conflict instead of silently choosing an
interpretation.

## AI Trading Intelligence Platform --- TradingView Data + Technical Analysis + MTF Signal + Backtest + Alert + SaaS

------------------------------------------------------------------------

# 0. INSTRUCTION QUAN TRỌNG CHO ANTIGRAVITY

Bạn là **Principal Software Architect + Quant Trading System Architect +
Backend Engineer + DevOps/SRE + Security Engineer**.

Nhiệm vụ của bạn KHÔNG phải lập tức viết code.

Trước tiên phải:

1.  Đọc toàn bộ repository hiện tại.
2.  Hiểu mục tiêu nghiệp vụ.
3.  Phân tích TradingView-API dependency.
4.  Phân tích kiến trúc hệ thống.
5.  Xác định các thành phần cần xây mới.
6.  Xác định những gì có thể reuse.
7.  Xác định rủi ro kỹ thuật.
8.  Xác định các rủi ro do TradingView private/internal API.
9.  Xác định các vấn đề về authentication, session, rate limit,
    reconnect, data consistency.
10. Lập Implementation Plan theo từng Phase.
11. Chia thành các Epic → Feature → Task → Subtask.
12. Xác định dependency giữa các task.
13. Xác định Definition of Done cho từng Phase.
14. Xác định test strategy.
15. Xác định observability strategy.
16. Xác định security strategy.
17. Xác định khả năng scale.
18. Xác định technical debt.
19. Xác định các phần cần POC trước khi implementation.
20. KHÔNG tự ý code toàn bộ hệ thống trước khi Implementation Plan được
    review và approved.

Antigravity phải tạo một Implementation Plan đủ chi tiết để một đội
engineering có thể triển khai hệ thống theo từng phase.

Sau khi tạo plan, DỪNG và chờ approval.

Không được tự suy diễn rằng tất cả các tính năng của TradingView-API đều
hoạt động production-ready.

Mọi capability liên quan TradingView phải được kiểm chứng trực tiếp bằng
source code, test hoặc POC.

------------------------------------------------------------------------

# V2.0 CONTROL LAYER --- READ BEFORE ALL ORIGINAL SECTIONS

## V2.0-001 --- Product Maturity Model

The platform must be implemented according to explicit maturity levels:

``` text
L0 — Research
L1 — Technical POC
L2 — Internal Alpha
L3 — Private Beta
L4 — Public Beta
L5 — Commercial SaaS
L6 — Enterprise
```

Every capability must be tagged with: - target maturity level -
prerequisite - verification state - production risk - legal/commercial
status - fallback - owner

Do not build a Commercial SaaS capability merely because it appears in
the final product vision.

------------------------------------------------------------------------

## V2.0-002 --- Feasibility Gates

Before major implementation, the following gates are mandatory:

1.  TradingView Technical Feasibility Gate
2.  TradingView Operational Stability Gate
3.  Data Quality Gate
4.  Quant Correctness Gate
5.  Performance/Scale Gate
6.  Security Gate
7.  Commercial/Legal Gate
8.  Production Readiness Gate

A failed gate is a blocker. Antigravity must:

``` text
STOP
→ explain evidence
→ identify impact
→ propose alternatives
→ update plan
→ WAIT FOR APPROVAL
```

------------------------------------------------------------------------

## V2.0-003 --- Capability Verification State

Every external capability must use one of:

``` text
UNKNOWN
SOURCE_VERIFIED
POC_VERIFIED
BENCHMARK_VERIFIED
PRODUCTION_VERIFIED
INVALIDATED
```

README claims are never sufficient.

The capability matrix must contain:

  ------------------------------------------------------------------------------------------------------
  Capability   Provider   Verification   Evidence   POC     Benchmark   Production   Legal    Fallback
                                                                        risk         status   
  ------------ ---------- -------------- ---------- ------- ----------- ------------ -------- ----------

  ------------------------------------------------------------------------------------------------------

------------------------------------------------------------------------

## V2.0-004 --- Assumption Register

Create:

``` text
docs/assumption-register.md
```

Each assumption must contain:

``` text
ASM-ID
Statement
Source
Status
Validation method
Owner
Impact
Fallback
```

Statuses:

``` text
UNKNOWN
VALIDATED
INVALIDATED
SUPERSEDED
```

Examples: - TradingView realtime remains usable for the required
workload. - One session can support the required number of studies. -
Shared subscriptions can reduce underlying sessions as expected. -
Historical data is sufficient for the required backtest horizon. - A
provider capability is commercially usable. - Node/Python boundary does
not create unacceptable serialization latency.

No assumption may silently become a fact.

------------------------------------------------------------------------

## V2.0-005 --- Provider Abstraction Is a Hard Architectural Boundary

The platform must be provider-agnostic.

Required abstraction:

``` typescript
interface MarketDataProvider
```

Potential implementations:

``` text
TradingViewProvider
MT5Provider
SSIProvider
DNSEProvider
BinanceProvider
CsvParquetProvider
FutureProvider
```

Business domains MUST NOT import TradingView-specific classes.

Forbidden dependencies:

``` text
Domain → TradingView
Strategy → TradingView
Signal → TradingView
Risk → TradingView
Backtest → TradingView
AI → TradingView
```

Allowed:

``` text
TradingViewAdapter → TradingView library/protocol
```

The architecture must allow a provider to be replaced without rewriting
Strategy, Signal, Risk, Backtest or UI.

------------------------------------------------------------------------

## V2.0-006 --- Provider Capability Contract

Every provider must expose capabilities explicitly.

Example:

``` typescript
interface ProviderCapabilities {
  realtime: boolean;
  historical: boolean;
  quotes: boolean;
  ohlcv: boolean;
  multiSymbol: boolean;
  multiTimeframe: boolean;
  builtInIndicators: boolean;
  pineIndicators: boolean;
  replay: boolean;
  screener: boolean;
}
```

Capability discovery must be runtime/configuration aware where
appropriate.

The system must gracefully degrade when a provider does not support a
capability.

------------------------------------------------------------------------

## V2.0-007 --- TradingView Private/Internal Protocol Risk

The TradingView integration is considered a **high-risk external
dependency** because the referenced implementation
reverse-engineers/internalizes a WebSocket protocol.

Antigravity must explicitly investigate:

-   WebSocket endpoint
-   protocol messages
-   session lifecycle
-   authentication
-   cookies/session identifiers
-   ping/pong
-   reconnect behavior
-   subscription lifecycle
-   symbol resolution
-   historical requests
-   realtime updates
-   error packets
-   protocol changes
-   disconnect patterns
-   HTTP 429 behavior
-   authentication expiry
-   possible anti-abuse/CAPTCHA behavior
-   IP/account restrictions
-   legal/commercial constraints

Do not claim stability merely because the library currently works.

------------------------------------------------------------------------

## V2.0-008 --- Mandatory TradingView POC-001: 24-Hour Stability

POC-001 is mandatory in Phase 1.

Objective:

> Demonstrate whether the TradingView adapter can maintain a stable
> realtime session for at least 24 continuous hours under a controlled
> workload.

Minimum experiment:

``` text
FPT M5
XAUUSD M1
representative multi-timeframe workload
```

Measure:

-   uptime
-   reconnect count
-   disconnect reason
-   authentication failures
-   429
-   protocol errors
-   missed candles
-   duplicate candles
-   out-of-order events
-   memory growth
-   CPU
-   network
-   event throughput
-   latency
-   subscription restoration time

Deliverable:

``` text
docs/poc/poc-001-tradingview-24h-stability.md
```

A 24-hour run is a validation experiment, not proof of indefinite
production stability.

------------------------------------------------------------------------

## V2.0-009 --- Mandatory TradingView POC-009: Rate Limit / WSS Disconnect

POC-009 must test:

1.  HTTP 429
2.  repeated reconnects
3.  WebSocket disconnect
4.  authentication expiry
5.  subscription restore
6.  cooldown
7.  exponential backoff + jitter
8.  circuit breaker
9.  stale connection detection

Required behavior:

``` text
429
→ classify
→ respect backoff/cooldown
→ avoid reconnect storm
→ preserve desired subscriptions
→ recover when safe
```

Never implement aggressive account rotation as a workaround without
explicit technical and legal approval.

------------------------------------------------------------------------

## V2.0-010 --- TradingView Study Capacity Benchmark

TradingView Premium study/session capacity must be **measured and
verified**, not assumed.

POC must determine, for the actual protocol/library:

-   maximum stable studies per Chart Session
-   behavior when adding studies
-   realtime update stability
-   memory/CPU growth
-   study removal behavior
-   multiple study types
-   built-in + Pine combinations
-   failure/drop behavior

Required benchmark matrix:

``` text
1 study
5
10
20
...
N
```

where N is increased until instability or provider limitation is
observed.

The final system must not assume unlimited simultaneous indicators.

------------------------------------------------------------------------

## V2.0-011 --- Shared Subscription Is a Core Optimization

Subscription Aggregator remains a core architectural capability.

Example:

``` text
User A → FPT M5
User B → FPT M5
User C → FPT M5

          ↓

One canonical FPT M5 stream
```

The aggregator must:

-   deduplicate subscriptions
-   reference-count consumers
-   merge identical requests
-   release unused streams
-   recover subscriptions after reconnect
-   expose subscription health
-   avoid duplicate provider sessions

Benchmark:

``` text
10 users
100 users
1,000 users
```

with shared and non-shared baselines.

------------------------------------------------------------------------

## V2.0-012 --- Canonical Market Data Contract

The canonical candle model must be expanded to:

``` text
event_id
provider
provider_symbol
internal_symbol
exchange
asset_class
currency
timezone
timeframe
source_timestamp
event_timestamp
received_at
processed_at

open
high
low
close
volume

is_closed
sequence
revision
quality_status
quality_score
```

Distinguish:

``` text
source_timestamp
received_at
processed_at
signal_timestamp
alert_timestamp
```

Latency must be measurable across the full chain.

------------------------------------------------------------------------

## V2.0-013 --- Forming vs Closed Candle

The engine MUST distinguish:

``` text
FORMING
CLOSED
```

A forming candle may update repeatedly.

A closed candle is immutable for the relevant timeframe unless the
provider explicitly reports a revision.

Rules:

-   No duplicate signal because of repeated forming updates.
-   Strategies must declare whether they operate on forming or closed
    candles.
-   Backtest default is closed-candle deterministic evaluation.
-   Signal evidence must record candle state.

------------------------------------------------------------------------

## V2.0-014 --- Vietnam Trading Session Engine

Vietnam market handling must explicitly model:

``` text
ATO
Continuous session
Lunch break
ATC
Negotiated/block trade where applicable
```

The exact official market schedule must be configuration-driven and
verified against the current exchange rules before production.

The system must not hard-code holiday/session rules.

The engine must support:

``` text
ExchangeCalendar
TradingSession
SessionSegment
Holiday
SpecialSession
EarlyClose
Suspension
```

For HOSE/HNX/UPCOM:

-   do not generate normal continuous-session signals during lunch break
-   treat ATO/ATC as distinct auction/session segments
-   do not interpret an auction result as a normal continuous sequence
    without explicit modeling
-   mark candle/session semantics so strategies can opt in/out
-   support session-specific signal policies

------------------------------------------------------------------------

## V2.0-015 --- Market Session Data Semantics

Each candle must be able to identify:

``` text
session_type
session_segment
is_auction
is_continuous
```

Strategies may declare:

``` text
allowed_session_types
blocked_session_types
```

Example:

``` text
VN_STOCK_BREAKOUT_V1
allowed:
  CONTINUOUS

blocked:
  ATO
  LUNCH
  ATC
```

unless explicitly designed otherwise.

------------------------------------------------------------------------

## V2.0-016 --- Fallback Static Data Provider

A first-class provider must exist for offline/static datasets:

``` text
CsvParquetProvider
```

Purpose:

-   backtest
-   replay
-   development
-   integration test
-   protocol-independent testing
-   TradingView outage fallback for historical analysis

Input:

``` text
CSV
Parquet
```

Required interface compatibility:

``` text
MarketDataProvider
```

This prevents the backtest engine from depending on live TradingView
availability.

------------------------------------------------------------------------

## V2.0-017 --- Dataset Versioning

Every backtest/replay must identify:

``` text
dataset_id
dataset_version
provider
source
download_time
coverage_start
coverage_end
timezone
adjustment_policy
quality_status
```

Backtest must be reproducible against the same dataset version.

------------------------------------------------------------------------

## V2.0-018 --- Raw vs Adjusted Market Data

For equities, support the distinction between:

``` text
raw_price
adjusted_price
adjustment_factor
corporate_action
```

Corporate actions must be modeled where applicable.

Backtest configuration must explicitly state whether adjusted or raw
data is used.

------------------------------------------------------------------------

## V2.0-019 --- Survivorship Bias

The backtest engine MUST prevent survivorship bias.

Universe membership must be historical where required.

Example:

``` text
VN30 at date T
```

must not automatically use today's VN30 membership for historical
periods.

Create:

``` text
HistoricalUniverseMembership
```

and include universe version in backtest metadata.

------------------------------------------------------------------------

## V2.0-020 --- Signal Reproducibility

Every signal must be reproducible.

Persist or reference:

``` text
signal_id
market_snapshot_id
dataset/version
strategy_version
indicator_version
model_version
rule_version
score_model_version
configuration_version
risk_model_version
```

Also persist evidence:

``` text
indicator values
MTF states
structure states
score components
entry
SL
TP
R:R
risk decision
```

Requirement:

> Same snapshot + same versions + same configuration must produce the
> same deterministic signal result.

------------------------------------------------------------------------

## V2.0-021 --- Score Is Not Probability and Not a Trade Decision

Separate:

``` text
Market Score
Setup Score
Signal Score
Confidence
Probability
Risk Decision
Trade Candidate
```

Recommended flow:

``` text
Market Features
→ Setup Evaluation
→ Score
→ Candidate Signal
→ Risk Engine
→ Validated Signal
```

A high score MUST NOT automatically imply:

``` text
BUY
or
high win probability
```

unless statistically calibrated and explicitly labeled.

------------------------------------------------------------------------

## V2.0-022 --- Score Model Versioning

Score weights must be configurable and versioned.

Example:

``` text
SCORE_MODEL_V1
Trend       25
Momentum    20
Volume      15
Structure   20
MTF         10
Risk        10
```

Persist:

``` text
score_model_version
weight configuration
feature contributions
thresholds
```

Never hard-code score weights in business logic.

------------------------------------------------------------------------

## V2.0-023 --- Candidate Signal vs Validated Signal

Signal lifecycle must distinguish:

``` text
Candidate
Validated
Active
Invalidated
Expired
Closed
```

Risk Engine must be able to reject a candidate:

``` text
Candidate Signal
→ Risk Filter
→ REJECT
```

Examples:

-   insufficient R:R
-   session invalid
-   max exposure exceeded
-   daily risk exceeded
-   abnormal spread/slippage
-   stale data
-   data quality failure

------------------------------------------------------------------------

## V2.0-024 --- Risk Engine Boundary

Target flow:

``` text
Market Data
→ Indicators
→ Structure
→ MTF
→ Strategy
→ Candidate Signal
→ Risk Engine
→ Validated Signal
→ Alert
```

Risk must not be an afterthought.

------------------------------------------------------------------------

## V2.0-025 --- Backtest Execution Model

Backtest must model execution rather than merely calculate indicator
outcomes.

At minimum evaluate:

``` text
market order
limit order
stop order
spread
slippage
commission
partial fill where applicable
latency assumptions
session constraints
position sizing
```

The assumptions must be visible in the result.

------------------------------------------------------------------------

## V2.0-026 --- Backtest Correctness Gates

Backtest correctness must include:

``` text
look-ahead bias
future leakage
survivorship bias
data snooping
overfitting
incorrect session handling
incorrect corporate-action handling
forming-candle leakage
execution timestamp errors
```

Required test suites must intentionally attempt to introduce these
errors and prove that the engine prevents/detects them.

------------------------------------------------------------------------

## V2.0-027 --- Live / Replay / Backtest Same-Logic Principle

The preferred architecture is:

``` text
Live Market Event
      ↓
Canonical Event
      ↓
Quant Engine
```

and:

``` text
Historical Dataset
      ↓
Replay Event
      ↓
Canonical Event
      ↓
Same Quant Engine
```

Do not maintain separate duplicated strategy logic for live and backtest
unless explicitly justified.

------------------------------------------------------------------------

## V2.0-028 --- Node.js + Python Boundary

Antigravity must explicitly evaluate:

``` text
Node.js/TypeScript
Python
```

Responsibilities may be:

``` text
Node.js:
- API
- WebSocket
- TradingView adapter
- realtime orchestration
- subscription aggregation

Python:
- quant research
- vectorized backtest
- optimization
- statistical analysis
- ML where justified
```

But this is NOT a mandatory architecture until benchmarked.

The boundary must be explicit.

Evaluate:

``` text
Redis Streams
gRPC
RabbitMQ
NATS
embedded worker
batch/object storage
```

based on actual workload.

Do not move every small calculation across processes.

------------------------------------------------------------------------

## V2.0-029 --- Serialization/IPC Benchmark

If Node and Python are both used, benchmark:

``` text
JSON
MessagePack
Protobuf
Arrow/Parquet for batch data
```

Measure:

-   serialization latency
-   deserialization latency
-   CPU
-   payload size
-   throughput
-   memory
-   backpressure

Use streaming/binary formats for high-volume paths where justified.

------------------------------------------------------------------------

## V2.0-030 --- Event Bus Decision Gate

Do not automatically deploy Kafka.

Compare:

``` text
Kafka
Redpanda
NATS
RabbitMQ
Redis Streams
in-process event bus
```

based on:

-   throughput
-   latency
-   replay
-   ordering
-   durability
-   operational complexity
-   cost
-   observability
-   team skill
-   deployment footprint

For early phases, a simpler event mechanism is acceptable if it meets
measured requirements.

------------------------------------------------------------------------

## V2.0-031 --- Database Decision Gate

Do not automatically deploy all of:

``` text
PostgreSQL
TimescaleDB
ClickHouse
Redis
Kafka
```

Benchmark candidate architectures and choose the minimum architecture
that meets the workload.

Potential baseline:

``` text
PostgreSQL + TimescaleDB + Redis
```

or another measured option.

------------------------------------------------------------------------

## V2.0-032 --- Workload Model

Scale must be defined by workload, not only user count.

Define:

``` text
users
active_users
symbols/user
unique_symbols
timeframes/symbol
indicators/symbol
alerts/user
API requests/user
backtests/day
AI requests/day
provider sessions
market events/sec
signal evaluations/sec
```

Example workload profiles:

``` text
Profile A: 100 users
Profile B: 1,000 users
Profile C: 10,000 users

Each with:
10 / 100 / 500 / 1,000 / 5,000 unique symbols
```

------------------------------------------------------------------------

## V2.0-033 --- Cost Model

Estimate:

``` text
compute
database
Redis
event bus
storage
network
AI
monitoring
data provider
```

Calculate:

``` text
cost / active user / month
cost / 1,000 symbols
cost / million events
cost / backtest
```

At:

``` text
100 users
1,000 users
10,000 users
```

Do not finalize SaaS pricing until workload and provider licensing
assumptions are validated.

------------------------------------------------------------------------

## V2.0-034 --- Telegram Delivery Architecture

Telegram must NOT be called synchronously from the Signal Engine.

Required:

``` text
Signal
→ Alert Event
→ Outbox/Queue
→ Telegram Worker
→ Rate Limiter
→ Telegram Adapter
```

Required capabilities:

-   global rate limiter
-   per-chat rate limiter
-   burst control
-   queue
-   retry
-   exponential backoff
-   flood-control handling
-   delivery status
-   dead-letter handling
-   deduplication
-   idempotency

The commonly cited limits (e.g. 30 messages/sec globally and 1
message/sec/chat) must be treated as **provider limits to verify against
current official Telegram documentation at implementation time**, not
immutable constants.

All rate limits must be configuration-driven.

------------------------------------------------------------------------

## V2.0-035 --- Alert Outbox Pattern

Signal creation must not depend on Telegram availability.

Preferred:

``` text
DB transaction
→ Signal persisted
→ Outbox event persisted
→ Worker delivers
```

If Telegram is down:

``` text
Signal remains valid
Alert delivery retries
```

The system must never lose a signal merely because an alert provider
failed.

------------------------------------------------------------------------

## V2.0-036 --- AI Grounding Contract

AI may only use:

``` text
market snapshot
indicator snapshot
MTF snapshot
strategy metadata
signal evidence
risk decision
backtest results
```

AI output should reference:

``` text
signal_id
evidence IDs
timestamp
strategy_version
dataset_version where applicable
```

AI must never invent market values.

------------------------------------------------------------------------

## V2.0-037 --- AI Grounding Test Suite

Create tests for:

-   unsupported claims
-   stale data
-   missing evidence
-   conflicting indicators
-   hallucinated prices
-   hallucinated scores
-   unsupported probability claims

AI must answer:

``` text
I don't have sufficient evidence.
```

when required.

------------------------------------------------------------------------

## V2.0-038 --- Multi-Tenant Isolation Test Suite

Tenant isolation must be tested across:

``` text
API
DB
cache
WebSocket
events
jobs
backtest
AI
alerts
audit
```

Example:

``` text
Tenant A requests Tenant B signal
→ denied
```

Do not rely only on UI filtering.

------------------------------------------------------------------------

## V2.0-039 --- Backend Entitlement Enforcement

Subscription restrictions must be enforced server-side.

Architecture:

``` text
User
→ Tenant
→ Subscription
→ Entitlement
→ Usage
→ Authorization
```

UI hiding is not security.

------------------------------------------------------------------------

## V2.0-040 --- Architecture Fitness Tests

Add automated dependency checks:

``` text
Domain MUST NOT import TradingView
Strategy MUST NOT import TradingView
Risk MUST NOT import TradingView
Backtest MUST NOT import TradingView
AI MUST NOT import TradingView
```

Provider-specific code must remain inside adapter/infrastructure
boundaries.

------------------------------------------------------------------------

## V2.0-041 --- Strategy DSL Timing

Do not build a full Strategy DSL in the earliest phase unless required.

First implement:

``` text
Code-based Strategy Interface
```

Build several real strategies.

Only then evaluate whether a JSON DSL/rule engine provides enough value
to justify:

-   parser
-   validator
-   versioning
-   debugger
-   execution model
-   serialization

------------------------------------------------------------------------

## V2.0-042 --- MVP Reclassification

The original MVP list is superseded by the following staged MVP:

### MVP-0 --- Data Proof

Must prove:

``` text
TradingView Adapter
Realtime OHLCV
Historical OHLCV
Symbol mapping
Canonical data
Forming/closed candle
Reconnect
429 handling
Gap detection
Duplicate detection
Static CSV/Parquet provider
```

Demo:

``` text
FPT M5
XAUUSD M1
```

No full signal engine required.

### MVP-1 --- Quant Foundation

Add:

``` text
EMA
RSI
MACD
ATR
Bollinger
MTF
basic Strategy Engine
basic Score Engine
Candidate Signal
Risk Engine
```

### MVP-2 --- Usable Trading Intelligence

Add:

``` text
Scanner
Validated Signal
Entry
SL
TP1/TP2/TP3
R:R
Telegram
Basic Dashboard
Backtest basic
Replay
Signal evidence
```

Ichimoku and advanced structure features may be added after the core
indicator abstraction is proven.

------------------------------------------------------------------------

## V2.0-043 --- Product Roadmap Override

Recommended roadmap:

``` text
PHASE 0   Discovery + Repository + Architecture
PHASE 0.5 TradingView Feasibility + Legal/Commercial Gate
PHASE 1   TradingView/Data POC
PHASE 2   Market Data Foundation
PHASE 3   Indicator Engine
PHASE 4   MTF + Market Structure
PHASE 5   Strategy + Score
PHASE 6   Signal + Risk
PHASE 7   Scanner + Watchlist
PHASE 8   Backtest + Replay
PHASE 9   Alert + Dashboard
PHASE 10  Paper Trading
PHASE 11  AI
PHASE 12  SaaS
PHASE 13  Production Hardening
```

The original Phase 0→12 roadmap remains the baseline concept but this
V2.0 sequence is authoritative where the two conflict.

------------------------------------------------------------------------

## V2.0-044 --- Commercial/Legal Readiness Gate

Commercial launch requires explicit review of:

``` text
TradingView Terms
Market Data Licensing
Redistribution
Commercial SaaS usage
Private/Pine indicator permissions
User-level access
Provider account limitations
```

Status must be:

``` text
CLEARED
REQUIRES LEGAL REVIEW
BLOCKED
```

Do not mark the product "commercial-ready" while a blocking licensing
assumption remains unresolved.

------------------------------------------------------------------------

## V2.0-045 --- Provider Independence KPI

Track:

``` text
Provider Independence Score
```

Target:

``` text
Domain logic independent of TradingView
Indicator engine minimally coupled
Strategy independent
Signal independent
Risk independent
Backtest independent
UI independent
```

A future provider replacement should primarily require:

``` text
new adapter
symbol mapping
data normalization mapping
capability mapping
```

not a rewrite of the trading intelligence layer.

------------------------------------------------------------------------

## V2.0-046 --- Decision Log

Create:

``` text
docs/decision-log.md
```

Track important choices:

``` text
Provider
Database
Event Bus
Cache
Node/Python boundary
Indicator execution
Strategy model
Backtest model
Multi-tenancy
Authentication
```

Each decision:

``` text
Context
Options
Decision
Reason
Trade-offs
Rejected alternatives
Date
Status
```

------------------------------------------------------------------------

## V2.0-047 --- Non-Functional Requirements

Antigravity must define measurable NFRs for:

### Availability

``` text
MVP target
Production target
99.9%
99.99% future target
```

### Latency

``` text
provider → ingestion
ingestion → processing
processing → signal
signal → alert
API p95/p99
WebSocket update
```

### Reliability

``` text
event loss
signal loss
alert loss
duplicate rate
```

### Recovery

``` text
RTO
RPO
```

Targets must be justified by benchmark, not guessed.

------------------------------------------------------------------------

## V2.0-048 --- Signal/Event Audit Model

Use:

``` text
Signal = current state
SignalEvent = immutable lifecycle history
```

Examples:

``` text
SIGNAL_CREATED
SIGNAL_CONFIRMED
SIGNAL_ACTIVATED
SIGNAL_INVALIDATED
SIGNAL_EXPIRED
SIGNAL_CLOSED
```

Every transition must be auditable and idempotent.

------------------------------------------------------------------------

## V2.0-049 --- Observability Latency Chain

Track:

``` text
source_timestamp
→ received_at
→ normalized_at
→ indicator_at
→ strategy_at
→ signal_at
→ alert_queued_at
→ alert_sent_at
```

Expose latency metrics:

``` text
market_data_ingestion_latency
indicator_latency
strategy_latency
signal_latency
alert_queue_latency
telegram_delivery_latency
end_to_end_latency
```

------------------------------------------------------------------------

## V2.0-050 --- Final V2.0 Non-Negotiable Rules

1.  Do not assume TradingView capability.
2.  Do not assume TradingView protocol stability.
3.  Do not assume Premium account licensing permits SaaS redistribution.
4.  Do not hard-code provider credentials.
5.  Do not hard-code signal rules.
6.  Do not hard-code score weights.
7.  Do not use future candles.
8.  Do not introduce survivorship bias.
9.  Do not let forming candles silently become closed-candle signals.
10. Do not make backtest dependent on live TradingView.
11. Do not make Telegram delivery synchronous with signal creation.
12. Do not create one provider connection per user when subscriptions
    can be shared.
13. Do not introduce Kafka/microservices without measured justification.
14. Do not create a full Strategy DSL before real strategies prove the
    need.
15. Do not let AI invent market facts.
16. Do not expose private indicator source without permission.
17. Do not implement broker execution in MVP.
18. Do not claim Score = probability.
19. Do not silently change approved architecture.
20. If a critical assumption becomes invalid: STOP, explain, update
    plan, request approval.

------------------------------------------------------------------------

# V2.0 --- UPDATED ANTIGRAVITY FIRST RESPONSE

The first response must contain, in this exact order:

1.  Repository inventory
2.  Existing architecture
3.  Reusable components
4.  Gaps
5.  TradingView source analysis
6.  TradingView protocol/capability matrix
7.  Capability verification state
8.  Assumption register
9.  TradingView feasibility result
10. Commercial/legal blockers
11. Provider abstraction proposal
12. Market data contract
13. Data quality strategy
14. Node/Python decision
15. Database decision
16. Event bus decision
17. Shared subscription architecture
18. POC plan
19. Benchmark plan
20. Quant correctness plan
21. Architecture proposal
22. Risk register
23. Phase roadmap
24. Dependency graph
25. MVP-0/MVP-1/MVP-2 scope
26. Non-MVP scope
27. Implementation plan
28. Blocking questions
29. Recommendation: GO / CONDITIONAL GO / NO-GO

Then:

``` text
STOP AND WAIT FOR USER APPROVAL.
```

------------------------------------------------------------------------

# V2.0 --- UPDATED APPROVAL PROTOCOL

No implementation is allowed until:

``` text
USER:
APPROVED — PROCEED
```

After every phase:

``` text
STOP
→ completed
→ changed files
→ tests
→ benchmark
→ incidents/issues
→ technical debt
→ risks
→ next phase
→ WAIT FOR APPROVAL
```

If implementation discovers a contradiction with the approved
architecture:

``` text
STOP
→ explain contradiction
→ show evidence
→ propose options
→ update affected ADR/plan
→ WAIT FOR APPROVAL
```

------------------------------------------------------------------------

# V2.0 --- FINAL PRODUCT PRINCIPLE

The product is not merely:

``` text
TradingView → Indicator → Signal
```

It is:

``` text
Provider
→ Canonical Market Data
→ Data Quality
→ Indicator
→ MTF
→ Structure
→ Strategy
→ Score
→ Candidate Signal
→ Risk
→ Validated Signal
→ Evidence
→ Backtest/Replay
→ Alert
→ Dashboard
→ AI Explanation
→ SaaS
```

with:

``` text
Provider Independence
+
Quant Correctness
+
Reproducibility
+
Observability
+
Security
+
Commercial Readiness
```

as first-class architectural requirements.

------------------------------------------------------------------------

# V2.0 --- FINAL COMMAND TO ANTIGRAVITY

``` text
DO NOT IMPLEMENT YET.

FIRST:

1. Inspect the entire repository.
2. Inspect package.json.
3. Inspect all source files relevant to TradingView.
4. Inspect tests and examples.
5. Inspect existing documentation.
6. Inspect the referenced TradingView-API repository/source.
7. Build the capability matrix.
8. Mark every capability UNKNOWN / SOURCE_VERIFIED / POC_VERIFIED / BENCHMARK_VERIFIED / PRODUCTION_VERIFIED.
9. Build the assumption register.
10. Build the TradingView feasibility assessment.
11. Build the commercial/legal risk assessment.
12. Build the provider abstraction.
13. Build the canonical market-data contract.
14. Build the data-quality strategy.
15. Analyze Node.js vs Python.
16. Analyze Redis Streams vs NATS vs RabbitMQ vs Kafka/Redpanda.
17. Analyze PostgreSQL/TimescaleDB vs ClickHouse.
18. Design shared subscription aggregation.
19. Design CSV/Parquet fallback provider.
20. Design POC-001 24-hour stability test.
21. Design POC-009 rate-limit/WSS-disconnect test.
22. Design the TradingView study-capacity benchmark.
23. Design data replay.
24. Design backtest correctness tests.
25. Design survivorship-bias and corporate-action handling.
26. Design signal reproducibility.
27. Design Telegram queue/rate limiter/outbox.
28. Design AI grounding tests.
29. Build risk register.
30. Build architecture proposal.
31. Build phase roadmap.
32. Build dependency graph.
33. Build MVP-0 / MVP-1 / MVP-2.
34. Build implementation plan.
35. Build task list.
36. Build Definition of Done and acceptance criteria.

DO NOT START BUSINESS FEATURE IMPLEMENTATION.

STOP AND WAIT FOR MY APPROVAL.
```

------------------------------------------------------------------------

# 1. BỐI CẢNH DỰ ÁN

Tôi muốn xây dựng một nền tảng:

## AI Trading Intelligence Platform

Mục tiêu là xây dựng hệ thống phân tích thị trường tài chính, trước mắt
tập trung vào:

-   Chứng khoán Việt Nam.
-   XAUUSD.
-   Có khả năng mở rộng sang Forex/Crypto/US Stocks sau này.

Hệ thống sử dụng TradingView làm một trong các nguồn dữ liệu và phân
tích quan trọng.

Repository tham khảo chính:

https://github.com/Mathieu2301/TradingView-API

TradingView-API hiện cung cấp nhiều capability như:

-   realtime market data
-   OHLCV
-   Chart Session
-   Quote Session
-   technical analysis
-   Built-in indicators
-   Pine indicators
-   invite-only indicators
-   realtime study values
-   drawings
-   replay
-   backtest
-   screener
-   hotlists
-   calendar
-   market search

Phải nghiên cứu trực tiếp source code để xác định capability nào thực sự
usable.

Không được coi README là source of truth duy nhất.

------------------------------------------------------------------------

# 2. MỤC TIÊU SẢN PHẨM

Xây dựng một nền tảng có khả năng:

1.  Theo dõi hàng nghìn mã.
2.  Thu thập dữ liệu realtime.
3.  Thu thập historical OHLCV.
4.  Chuẩn hóa dữ liệu.
5.  Tính technical indicators.
6.  Sử dụng TradingView built-in indicators.
7.  Sử dụng Pine indicators khi được phép.
8.  Phân tích Multi-Timeframe.
9.  Phân tích trend.
10. Phân tích momentum.
11. Phân tích volatility.
12. Phân tích volume.
13. Phân tích market structure.
14. Phân tích supply/demand.
15. Phân tích order block.
16. Phân tích liquidity.
17. Phân tích breakout.
18. Tính điểm Trading Score.
19. Sinh Entry.
20. Sinh Stop Loss.
21. Sinh TP1/TP2/TP3.
22. Tính Risk/Reward.
23. Tính confidence.
24. Sinh cảnh báo realtime.
25. Gửi Telegram.
26. Có Web Dashboard.
27. Có API.
28. Có watchlist.
29. Có scanner.
30. Có backtesting.
31. Có strategy optimization.
32. Có paper trading.
33. Có trade journal.
34. Có portfolio/risk management.
35. Có user/account system.
36. Có subscription/billing architecture.
37. Có multi-tenant architecture.
38. Có audit log.
39. Có observability.
40. Có khả năng thương mại hóa SaaS.

------------------------------------------------------------------------

# 3. TRIẾT LÝ KIẾN TRÚC

Không được xây hệ thống theo kiểu:

User → TradingView-API → TradingView → Signal

Phải xây theo abstraction layer.

Kiến trúc mục tiêu:

TradingView ↓ TradingView Adapter ↓ Market Data Gateway ↓ Data
Normalization ↓ Market Data Bus ↓ Market Data Storage ↓ Indicator Engine
↓ Market Structure Engine ↓ Strategy Engine ↓ Signal Engine ↓ Risk
Engine ↓ Alert Engine ↓ API ↓ Web / Mobile / Telegram

TradingView-API chỉ là một provider/adapter.

Không để business logic phụ thuộc trực tiếp vào class của
TradingView-API.

------------------------------------------------------------------------

# 4. NGUYÊN TẮC PROVIDER ABSTRACTION

Thiết kế:

interface MarketDataProvider

Ví dụ:

TradingViewProvider MT5Provider BinanceProvider OtherProvider

Business layer chỉ làm việc với:

MarketDataProvider

Không import trực tiếp TradingView Client trong:

-   Signal Engine
-   Strategy Engine
-   Risk Engine
-   User Service
-   Notification Service

------------------------------------------------------------------------

# 5. KIẾN TRÚC MICROSERVICE / MODULAR MONOLITH

Trước khi quyết định microservices, hãy phân tích:

-   Modular monolith
-   Microservices
-   Event-driven architecture

Không được mặc định microservices nếu chưa có lý do.

Đề xuất ưu tiên:

Phase đầu:

Modular Monolith + Worker architecture

Sau khi scale:

tách thành services.

Phải đưa ra rationale.

------------------------------------------------------------------------

# 6. CÁC DOMAIN CHÍNH

Thiết kế domain:

## 6.1 Identity

-   User
-   Role
-   Permission
-   Session
-   API Key
-   Device
-   Authentication

## 6.2 Subscription

-   Plan
-   Subscription
-   Feature entitlement
-   Usage quota
-   Billing
-   Trial

## 6.3 Market

-   Exchange
-   Market
-   Symbol
-   Symbol mapping
-   Instrument
-   Trading session
-   Tick
-   Candle

## 6.4 Watchlist

-   Watchlist
-   Watchlist item
-   User symbol subscription

## 6.5 Market Data

-   Realtime data
-   Historical data
-   Candle stream
-   Quote stream
-   Data provider
-   Data quality

## 6.6 Indicator

-   Built-in indicator
-   Pine indicator
-   Custom indicator
-   Indicator definition
-   Indicator input
-   Indicator output
-   Plot
-   Indicator version

## 6.7 Strategy

-   Strategy
-   Strategy version
-   Strategy configuration
-   Strategy rules
-   Strategy parameters

## 6.8 Signal

-   Signal
-   Signal event
-   Signal score
-   Signal state
-   Entry
-   Stop Loss
-   Take Profit

## 6.9 Risk

-   Position sizing
-   Risk percentage
-   Max loss
-   R:R
-   Portfolio exposure

## 6.10 Backtest

-   Backtest job
-   Backtest dataset
-   Strategy version
-   Parameters
-   Trades
-   Metrics
-   Equity curve
-   Drawdown

## 6.11 Alert

-   Alert rule
-   Alert condition
-   Alert channel
-   Telegram
-   Web notification
-   Email
-   Webhook

## 6.12 Portfolio

-   Account
-   Position
-   Order
-   Trade
-   PnL
-   Portfolio risk

## 6.13 AI

-   Market explanation
-   Signal explanation
-   Strategy assistant
-   Trade journal analysis
-   Natural language query

------------------------------------------------------------------------

# 7. TRADINGVIEW-API RESEARCH REQUIREMENT

Phải nghiên cứu trực tiếp:

src/client.js src/protocol.js src/chart/session.js src/chart/study.js
src/chart/graphicParser.js src/quote/session.js src/quote/market.js
src/classes/PineIndicator.js src/classes/BuiltInIndicator.js
src/classes/PinePermManager.js src/miscRequests.js src/types.js
src/utils.js

Phải đọc:

examples/

và:

tests/

Đặc biệt kiểm tra:

-   ChartSession
-   QuoteSession
-   Study
-   PineIndicator
-   BuiltInIndicator
-   Replay
-   authentication
-   realtime
-   search
-   screener
-   drawings
-   indicator permissions

------------------------------------------------------------------------

# 8. TRADINGVIEW PROTOCOL

Phải xác định:

-   WebSocket endpoint.
-   Connection lifecycle.
-   Session ID.
-   Chart session.
-   Quote session.
-   Study session.
-   Packet format.
-   Message encoding.
-   Compression.
-   Ping/pong.
-   Authentication.
-   Error handling.
-   Reconnect.
-   Subscription.
-   Unsubscription.
-   Historical data request.
-   Realtime update.
-   Symbol resolution.

Phải tạo tài liệu:

docs/tradingview-protocol.md

Không được expose credential/session token trong log.

------------------------------------------------------------------------

# 9. TRADINGVIEW AUTHENTICATION

Phải phân tích:

-   Anonymous access.
-   Authenticated access.
-   Premium account.
-   Session token.
-   Authentication cookie.
-   Session lifecycle.
-   Expiration.
-   Multi-account.
-   Credential storage.

Không được hard-code:

username password sessionid auth token

Không commit secrets.

Phải sử dụng:

environment variables secret manager

Phải đánh giá:

Có được phép sử dụng TradingView account theo cách này trong môi trường
SaaS/commercial hay không.

Không được assume rằng TradingView subscription của một account có thể
dùng để phục vụ vô hạn user.

------------------------------------------------------------------------

# 10. MULTI-ACCOUNT TRADINGVIEW

Thiết kế abstraction:

TradingViewAccountPool

Có:

-   account_id
-   credential reference
-   status
-   health
-   rate limit
-   connection count
-   last error
-   last success
-   quota
-   assigned symbols

Thiết kế:

Account ↓ Connection Pool ↓ Session Pool ↓ Market Data

Phải có:

-   account health check
-   failover
-   cooldown
-   rate limit
-   reconnect
-   circuit breaker

Nhưng không tự động triển khai account rotation nếu chưa xác định
compliance/legal implications.

------------------------------------------------------------------------

# 11. MARKET DATA MODEL

Canonical Candle:

{ symbol, exchange, timeframe, timestamp, open, high, low, close,
volume, source, quality, is_closed }

Phải phân biệt:

-   forming candle
-   closed candle

Đây là requirement bắt buộc.

Không được trigger signal giống nhau trên forming candle và closed
candle.

------------------------------------------------------------------------

# 12. TIMEFRAME

Phải hỗ trợ:

1m 3m 5m 15m 30m 1h 2h 4h 1D 1W 1M

Có khả năng mở rộng.

Phải chuẩn hóa:

timeframe code.

Ví dụ:

TV_1 TV_5 TV_15 TV_60 TV_240 TV_1D

Không hard-code logic timeframe trong business layer.

------------------------------------------------------------------------

# 13. MULTI-TIMEFRAME ENGINE

MTF là một core capability.

Ví dụ:

M1 → entry

M5 → setup

M15 → confirmation

H1 → trend

H4 → macro trend

D1 → major trend

Engine phải hỗ trợ:

-   trend alignment
-   momentum alignment
-   structure alignment
-   volatility alignment
-   volume alignment

Ví dụ:

M1 bullish M5 bullish M15 bullish H1 bullish H4 bullish

→ strong bullish alignment.

------------------------------------------------------------------------

# 14. DATA STORAGE

Phân tích:

Redis PostgreSQL TimescaleDB ClickHouse

Đề xuất architecture dựa trên workload.

Phải lưu:

-   raw market data nếu cần
-   normalized candles
-   indicator values
-   signals
-   trades
-   backtest results

Redis:

-   latest price
-   latest candle
-   active signals
-   hot cache

Time-series database:

-   historical candles
-   indicator series

PostgreSQL:

-   metadata
-   users
-   strategies
-   signals
-   trades
-   configurations

------------------------------------------------------------------------

# 15. DATA INGESTION

Xây:

MarketDataGateway

Có:

-   provider adapter
-   connection manager
-   subscription manager
-   symbol manager
-   stream manager
-   reconnect manager
-   data validator
-   deduplicator
-   gap detector

Pipeline:

Provider → Raw Event → Parser → Normalizer → Validator → Deduplicator →
Event Bus → Storage → Consumers

------------------------------------------------------------------------

# 16. REALTIME ENGINE

Phải hỗ trợ:

-   realtime price
-   realtime candle
-   candle close
-   indicator update
-   signal update

Event types:

PRICE_UPDATE CANDLE_UPDATE CANDLE_CLOSED INDICATOR_UPDATE SIGNAL_CREATED
SIGNAL_UPDATED SIGNAL_INVALIDATED

Thiết kế event schema versioning.

------------------------------------------------------------------------

# 17. CONNECTION MANAGEMENT

Phải xây:

ConnectionManager

Có:

-   connect
-   disconnect
-   reconnect
-   exponential backoff
-   jitter
-   heartbeat
-   health check
-   session recreation
-   subscription restore
-   stale connection detection

Phải xử lý:

HTTP 429 5xx WebSocket close auth failure protocol error timeout
malformed packet

------------------------------------------------------------------------

# 18. RATE LIMITING --- SEE V2.0-011 AND V2.0-034

Phải có:

-   per provider
-   per account
-   per connection
-   per user
-   per API endpoint

Không được để:

100 users × 100 symbols

tạo 10,000 independent TradingView connections nếu có thể share stream.

Phải xây:

Subscription Aggregator

Ví dụ:

User A cần FPT M5 User B cần FPT M5 User C cần FPT M5

→ chỉ cần một underlying stream.

------------------------------------------------------------------------

# 19. SYMBOL MASTER

Phải xây Symbol Master.

Ví dụ:

HOSE:FPT HOSE:MWG HOSE:HPG

Phải có:

-   symbol
-   exchange
-   country
-   currency
-   asset type
-   trading session
-   timezone
-   TradingView symbol
-   internal symbol
-   provider symbol

Phải có Symbol Mapping.

------------------------------------------------------------------------

# 20. VIETNAM MARKET --- SEE V2.0-014 AND V2.0-015

Phase đầu tập trung:

HOSE HNX UPCOM

Phải hỗ trợ:

-   VNINDEX
-   VN30
-   sector/index nếu khả dụng
-   stock
-   ETF nếu cần

Phải xác định:

Trading session Timezone Holiday Market open Market close Lunch break
nếu có

Không hard-code holiday.

------------------------------------------------------------------------

# 21. TECHNICAL INDICATOR ENGINE

Phải hỗ trợ tối thiểu:

EMA SMA WMA RSI MACD Bollinger Bands ATR ADX CCI RVI Stochastic Ichimoku
Volume VWAP

Sau đó:

Supply/Demand Order Block Fair Value Gap BOS CHoCH Liquidity Swing
High/Low

------------------------------------------------------------------------

# 22. TRADINGVIEW BUILT-IN INDICATORS

Phải nghiên cứu:

BuiltInIndicator

và:

ChartStudy

Xác định:

-   cách tạo study
-   cách truyền input
-   cách lấy plot
-   cách nhận realtime update
-   cách xử lý error
-   cách remove study
-   cách multiple studies

Không assume Unlimited simultaneous indicators là unlimited trong
production.

Phải benchmark.

------------------------------------------------------------------------

# 23. PINE INDICATOR

Phải nghiên cứu sâu:

PineIndicator

Phải xác định:

-   indicator metadata
-   inputs
-   plots
-   version
-   script ID
-   access
-   private
-   invite-only
-   open-source

Phải tạo:

Indicator Registry

Ví dụ:

{ id, name, provider, type, version, inputs, plots, access, status }

------------------------------------------------------------------------

# 24. PINE INDICATOR EXECUTION

Phải xác định chính xác:

TradingView server execute Pine script hay local engine.

Ưu tiên:

TradingView execution nếu hợp lệ và ổn định.

Không copy/private Pine source nếu không được phép.

Phải tách:

Indicator Metadata Indicator Configuration Indicator Execution Indicator
Output

------------------------------------------------------------------------

# 25. INDICATOR OUTPUT

Chuẩn hóa:

{ symbol, timeframe, indicator, timestamp, plot, value }

Ví dụ:

RSI:

plot = rsi value = 67.2

MACD:

macd signal histogram

Ichimoku:

tenkan kijun senkouA senkouB chikou

------------------------------------------------------------------------

# 26. INDICATOR CACHE

Không tính lại cùng một indicator nhiều lần.

Key:

provider:symbol:timeframe:indicator:config

Ví dụ:

tv:FPT:5m:RSI:14

Nếu 100 users cùng cần:

FPT M5 RSI14

→ share result.

------------------------------------------------------------------------

# 27. TECHNICAL ANALYSIS ENGINE

Phải hỗ trợ:

-   trend
-   momentum
-   volatility
-   volume
-   moving average
-   oscillator

Phải có normalized score.

Ví dụ:

Trend Score: 0--25 Momentum Score: 0--20 Volume Score: 0--15 Structure
Score: 0--20 MTF Score: 0--10 Risk Score: 0--10

Total:

0--100

------------------------------------------------------------------------

# 28. SIGNAL ENGINE

Signal phải có lifecycle:

WATCH SETUP TRIGGERED CONFIRMED ACTIVE INVALIDATED EXPIRED CLOSED

Không tạo signal duplicate.

Signal ID phải idempotent.

------------------------------------------------------------------------

# 29. ENTRY ENGINE

Phải hỗ trợ:

-   market entry
-   breakout entry
-   pullback entry
-   retest entry
-   limit entry

Entry phải có:

price time reason strategy confidence

------------------------------------------------------------------------

# 30. STOP LOSS ENGINE

Các phương pháp:

-   fixed percentage
-   ATR
-   swing low/high
-   structure-based
-   order block
-   volatility-based

Ví dụ:

Long:

SL = swing low - buffer

Short:

SL = swing high + buffer

------------------------------------------------------------------------

# 31. TAKE PROFIT ENGINE

Hỗ trợ:

TP1 TP2 TP3

Phương pháp:

-   fixed R:R
-   resistance/support
-   Fibonacci
-   ATR
-   structure
-   liquidity

Ví dụ:

Entry = 100 SL = 98

Risk = 2

TP1 = 102 TP2 = 104 TP3 = 106

------------------------------------------------------------------------

# 32. RISK ENGINE

Phải hỗ trợ:

risk per trade max daily loss max portfolio loss max concurrent
positions max exposure position sizing

Ví dụ:

Account = \$10,000

Risk = 1%

Max loss = \$100

Position size phải được tính dựa trên:

Entry SL Risk

------------------------------------------------------------------------

# 33. SIGNAL CONFIDENCE

Confidence không được đồng nghĩa với probability.

Phải phân biệt:

Score Confidence Probability

Nếu không có statistical model thì không được gọi score 90 là "90% win
probability".

------------------------------------------------------------------------

# 34. STRATEGY ENGINE

Strategy phải configurable.

Ví dụ:

EMA Trend Strategy RSI Reversal MACD Momentum Ichimoku Trend Breakout
Supply/Demand Order Block MTF Confluence

Strategy phải versioned.

Ví dụ:

EMA-MTF-v1 EMA-MTF-v2

Backtest phải ghi lại strategy version.

------------------------------------------------------------------------

# 35. STRATEGY CONFIGURATION

Ví dụ:

{ timeframe: "5m", emaFast: 20, emaSlow: 50, rsiPeriod: 14, rsiMin: 50,
riskPercent: 1, rr: 2 }

Không hard-code parameter.

------------------------------------------------------------------------

# 36. BACKTEST ENGINE

Phải hỗ trợ:

historical candles strategy parameters commission slippage spread
session initial capital

Output:

total trades win rate loss rate profit factor expectancy net profit max
drawdown Sharpe average R largest win largest loss consecutive wins
consecutive losses

------------------------------------------------------------------------

# 37. BACKTEST DATA INTEGRITY

Không được look-ahead bias.

Không được sử dụng:

future candle

để quyết định:

past trade.

Phải xử lý:

forming candle.

Phải phân biệt:

signal timestamp execution timestamp.

------------------------------------------------------------------------

# 38. REPLAY ENGINE

Nghiên cứu TradingView replay capability.

Nếu sử dụng được:

Historical Data → Replay Clock → Candle Event → Strategy Engine → Signal
→ Virtual Order → PnL

Mục tiêu:

Paper Trading Simulator.

------------------------------------------------------------------------

# 39. OPTIMIZATION ENGINE

Cho phép:

Grid Search Random Search Bayesian Optimization

Ví dụ:

EMA fast: 5--20

EMA slow: 30--100

RSI: 10--20

RR: 1.5--4

Output:

Best parameters

Nhưng phải chống overfitting.

Phải có:

train period validation period test period

------------------------------------------------------------------------

# 40. WALK-FORWARD TESTING

Phải thiết kế:

Train → Validate → Test → Move window → Repeat

Không chỉ chọn parameter tốt nhất trên toàn bộ dataset.

------------------------------------------------------------------------

# 41. SCANNER

Scanner phải hỗ trợ:

Universe:

HOSE HNX UPCOM VN30 Watchlist

Filter:

Price Volume RSI MACD EMA ADX ATR Breakout Gap Relative Volume Trend MTF
alignment

------------------------------------------------------------------------

# 42. SCANNER RESULT

Ví dụ:

FPT Score 91 Trend Bullish Momentum Strong Volume Strong MTF Strong
Setup Breakout

MWG Score 87

HPG Score 81

------------------------------------------------------------------------

# 43. WATCHLIST

User có thể:

-   create watchlist
-   rename
-   delete
-   add symbol
-   remove symbol
-   reorder
-   assign strategy
-   assign alert

------------------------------------------------------------------------

# 44. ALERT ENGINE

Alert types:

PRICE_ABOVE PRICE_BELOW CANDLE_CLOSE INDICATOR_CROSS RSI MACD EMA
BREAKOUT SIGNAL SL TP

Alert phải có:

deduplication cooldown retry delivery status

------------------------------------------------------------------------

# 45. TELEGRAM --- SEE V2.0-034 AND V2.0-035

Phase sau tích hợp:

Telegram Bot

Flow:

Signal → Alert Engine → Telegram Adapter → Telegram

Message phải chứa:

Symbol Timeframe Direction Entry SL TP1 TP2 TP3 RR Score Reason
Timestamp

------------------------------------------------------------------------

# 46. WEBHOOK

Hỗ trợ:

POST /webhooks/alerts

Payload versioned.

Có:

HMAC signature timestamp nonce replay protection

------------------------------------------------------------------------

# 47. WEB DASHBOARD

Dashboard phải có:

## Market Overview

-   VNINDEX
-   VN30
-   market breadth
-   top gainers
-   top losers
-   volume
-   sector

## Watchlist

-   realtime price
-   change
-   volume
-   score
-   trend

## Scanner

-   filters
-   score
-   setup

## Chart

-   candles
-   indicators
-   signals
-   Entry
-   SL
-   TP

## Signal Detail

-   score
-   reasons
-   MTF
-   indicators
-   risk

## Backtest

-   equity curve
-   drawdown
-   trade list
-   metrics

------------------------------------------------------------------------

# 48. AI LAYER

AI không được tự quyết định trade mà không có deterministic engine.

Architecture:

Market Data → Quant Engine → Signal Engine → AI Explanation

AI dùng để:

-   explain signal
-   summarize market
-   explain strategy
-   compare strategies
-   analyze journal
-   answer natural language questions

Ví dụ:

"Why FPT is bullish?"

AI phải lấy evidence:

EMA20 \> EMA50 RSI = 63 MACD bullish M15/H1 aligned Volume \> AVG20

Không được hallucinate.

------------------------------------------------------------------------

# 49. AI TRADING ASSISTANT

User có thể hỏi:

"Top 10 cổ phiếu bullish hôm nay?"

"FPT có setup breakout không?"

"Cho tôi các mã RSI oversold nhưng trend H1 vẫn bullish."

"Backtest EMA20/50 cho FPT 2 năm."

AI phải gọi tools/backend APIs.

Không để AI tự tính dữ liệu không có source.

------------------------------------------------------------------------

# 50. USER SYSTEM

Multi-user.

Role:

USER PRO ADMIN QUANT SUPPORT

Phải có:

RBAC API key session audit log

------------------------------------------------------------------------

# 51. MULTI-TENANT

Tenant isolation.

User A không thấy:

User B:

-   watchlist
-   strategy
-   signals
-   portfolio
-   API keys
-   trade journal

------------------------------------------------------------------------

# 52. SaaS PLAN

Thiết kế:

FREE PRO PREMIUM ENTERPRISE

Feature entitlement:

-   max watchlists
-   max symbols
-   max alerts
-   max strategies
-   max backtests
-   max API requests
-   realtime access

------------------------------------------------------------------------

# 53. USAGE METERING

Track:

market subscriptions indicator executions backtest jobs API requests
alerts AI tokens

Không được hard-code quota.

------------------------------------------------------------------------

# 54. API

Thiết kế REST API.

Có thể bổ sung WebSocket API.

Ví dụ:

GET /api/v1/symbols GET /api/v1/markets GET /api/v1/candles GET
/api/v1/quotes GET /api/v1/indicators GET /api/v1/scanner GET
/api/v1/signals POST /api/v1/backtests GET /api/v1/backtests/:id GET
/api/v1/strategies POST /api/v1/alerts

API version:

/api/v1

------------------------------------------------------------------------

# 55. API IDEMPOTENCY

Các API tạo:

signal alert backtest order

phải hỗ trợ idempotency.

------------------------------------------------------------------------

# 56. SECURITY

Bắt buộc:

-   secrets management
-   encryption
-   HTTPS
-   JWT/session security
-   RBAC
-   rate limit
-   API key rotation
-   audit logs
-   input validation
-   SQL injection protection
-   SSRF protection
-   webhook signature
-   CSRF nếu cần
-   secure headers

Không log:

password TradingView credentials session tokens API secrets

------------------------------------------------------------------------

# 57. OBSERVABILITY

Phải có:

Metrics Logs Tracing

Metrics:

connection_count active_symbols candle_latency indicator_latency
signal_latency queue_depth reconnect_count 429_count provider_errors
backtest_duration

------------------------------------------------------------------------

# 58. DISTRIBUTED TRACING

Nếu microservice:

trace:

TradingView → Market Gateway → Kafka → Indicator → Signal → Alert →
Telegram

Correlation ID:

trace_id

------------------------------------------------------------------------

# 59. LOGGING

Structured JSON logs.

Ví dụ:

{ timestamp, level, service, trace_id, user_id, symbol, timeframe,
event, duration, error }

Không log secrets.

------------------------------------------------------------------------

# 60. ALERTING

Monitoring alert:

TradingView connection down Data stale Candle gap 429 spike Kafka lag
Redis unavailable DB slow Signal engine error Telegram delivery failed

------------------------------------------------------------------------

# 61. TESTING

Phải có:

Unit Test Integration Test Contract Test E2E Test Load Test Chaos Test

TradingView adapter phải có mock protocol.

Không phụ thuộc TradingView live cho toàn bộ CI.

------------------------------------------------------------------------

# 62. DATA REPLAY TEST

Phải có khả năng record:

TradingView WebSocket event

và replay offline.

Mục tiêu:

Protocol regression testing.

------------------------------------------------------------------------

# 63. LOAD TEST

Benchmark tối thiểu:

100 symbols 500 symbols 1,000 symbols 5,000 symbols

Timeframes:

M1 M5 M15 H1

Phải đo:

CPU RAM network latency throughput connections messages/sec

------------------------------------------------------------------------

# 64. TARGET SCALE

Thiết kế để có thể mở rộng:

10 users 100 users 1,000 users 10,000 users

Không cần triển khai scale 10,000 user ngay phase đầu.

Nhưng architecture không được khóa cứng.

------------------------------------------------------------------------

# 65. HIGH AVAILABILITY

Mục tiêu production:

99.9% trước.

Sau đó:

99.99%.

Phải có:

-   health checks
-   graceful shutdown
-   reconnect
-   worker recovery
-   database backup
-   Redis failover nếu cần
-   queue retry

------------------------------------------------------------------------

# 66. FAILURE SCENARIOS

Phải phân tích ít nhất:

1.  TradingView disconnect.
2.  TradingView HTTP 429.
3.  TradingView auth expired.
4.  Symbol unavailable.
5.  Candle gap.
6.  Duplicate candle.
7.  Out-of-order event.
8.  Redis down.
9.  DB down.
10. Kafka down.
11. Telegram down.
12. Indicator error.
13. Pine study error.
14. Backtest worker crash.
15. User subscription expires.
16. Network partition.
17. Server restart.
18. Partial deployment.
19. Duplicate signal.
20. Duplicate alert.

Mỗi scenario phải có:

Detection Recovery Retry Fallback Alert Audit

------------------------------------------------------------------------

# 67. TRADING SAFETY

Hệ thống mặc định:

ANALYSIS ONLY

Không tự động đặt real-money order trong MVP.

Nếu sau này hỗ trợ broker execution:

phải tạo riêng:

Execution Engine

với:

kill switch max loss max position max order slippage control duplicate
prevention manual approval

------------------------------------------------------------------------

# 68. LEGAL / COMPLIANCE

Phải có một section riêng:

"TradingView Terms / Data Licensing / Commercial Usage Risk"

Không được giả định rằng:

TradingView Premium account

cho phép:

resell redistribute serve data to other users commercial SaaS

Phải đánh dấu:

REQUIRES LEGAL REVIEW

Đối với mọi feature liên quan redistribution/private indicators.

------------------------------------------------------------------------

# 69. PHASE ROADMAP

Antigravity phải đề xuất roadmap theo phase.

Tối thiểu:

## PHASE 0 --- Discovery & Architecture

Không code business feature.

Deliverables:

-   architecture
-   dependency map
-   risk register
-   TradingView capability matrix
-   POC plan
-   ADR

------------------------------------------------------------------------

## PHASE 1 --- TradingView Adapter POC

Mục tiêu:

-   connect
-   auth
-   realtime
-   OHLCV
-   symbol
-   timeframe
-   reconnect
-   error handling

Output:

FPT M5 realtime

và:

XAUUSD M1 realtime

------------------------------------------------------------------------

## PHASE 2 --- Market Data Platform

-   canonical model
-   Redis
-   PostgreSQL/Timescale
-   ingestion
-   normalization
-   subscription manager
-   caching
-   gap detection

------------------------------------------------------------------------

## PHASE 3 --- Indicator Engine

-   built-in
-   Pine
-   RSI
-   MACD
-   EMA
-   Bollinger
-   Ichimoku
-   ATR
-   ADX
-   CCI
-   RVI

------------------------------------------------------------------------

## PHASE 4 --- MTF Analysis

M1 M5 M15 H1 H4 D1

Build:

MTF Confluence Engine.

------------------------------------------------------------------------

## PHASE 5 --- Scanner

VN market scanner.

Universe:

HOSE HNX UPCOM VN30

------------------------------------------------------------------------

## PHASE 6 --- Signal Engine

-   setup
-   entry
-   SL
-   TP
-   R:R
-   confidence
-   score
-   lifecycle

------------------------------------------------------------------------

## PHASE 7 --- Backtest

-   historical
-   replay
-   trade simulation
-   metrics
-   optimization

------------------------------------------------------------------------

## PHASE 8 --- Alert

-   Telegram
-   Webhook
-   Email
-   Web push

------------------------------------------------------------------------

## PHASE 9 --- Web Dashboard

-   watchlist
-   scanner
-   chart
-   signal
-   backtest
-   portfolio

------------------------------------------------------------------------

## PHASE 10 --- AI Assistant

-   signal explanation
-   market analysis
-   strategy assistant
-   natural language query

------------------------------------------------------------------------

## PHASE 11 --- SaaS

-   multi-tenant
-   subscription
-   quota
-   billing
-   RBAC
-   API keys

------------------------------------------------------------------------

## PHASE 12 --- Production Hardening

-   HA
-   observability
-   security
-   load test
-   chaos test
-   disaster recovery
-   deployment automation

------------------------------------------------------------------------

# 70. PHASE GATING

Không được chuyển Phase nếu chưa đạt:

Architecture Gate Development Gate Test Gate Performance Gate Security
Gate Operational Gate

Ví dụ:

PHASE 1 PASS nếu:

-   realtime stable \>= X hours
-   reconnect tested
-   no memory leak
-   no duplicate candles
-   latency measured
-   errors handled
-   metrics available

------------------------------------------------------------------------

# 71. DEFINITION OF DONE

Mỗi feature phải có:

Code Unit test Integration test nếu cần Documentation Logging Metrics
Error handling Security review Performance consideration Migration nếu
cần Rollback plan

Không chấp nhận:

"works on my machine"

------------------------------------------------------------------------

# 72. DATABASE REQUIREMENT

Antigravity phải thiết kế ERD.

Tối thiểu:

users tenants subscriptions plans symbols markets watchlists
watchlist_items indicators indicator_configs strategies
strategy_versions signals signal_events alerts alert_deliveries
backtests backtest_trades portfolios positions trades audit_logs

------------------------------------------------------------------------

# 73. EVENT MODEL

Thiết kế event schema.

Ví dụ:

CandleClosedEvent

{ eventId, eventType, version, timestamp, source, symbol, timeframe,
candle }

Phải version event.

------------------------------------------------------------------------

# 74. CACHE STRATEGY

Xác định TTL cho:

quote candle indicator scanner signal

Không cache sai dữ liệu realtime.

------------------------------------------------------------------------

# 75. DATA QUALITY ENGINE

Phải kiểm tra:

missing candle duplicate candle invalid OHLC negative volume timestamp
issue timezone issue price spike provider inconsistency

Data Quality Score.

------------------------------------------------------------------------

# 76. MARKET SESSION ENGINE --- SEE V2.0-014 AND V2.0-015

Phải hiểu:

pre-market nếu có market-open market-close holiday half-day lunch break

Không chạy signal ngoài session nếu strategy không cho phép.

------------------------------------------------------------------------

# 77. STRATEGY DSL

Phân tích khả năng tạo:

Strategy Definition Language

Ví dụ:

IF EMA20 \> EMA50 AND RSI \> 50 AND Volume \> SMA20(Volume) AND M15
trend bullish THEN BUY

Phải đánh giá:

JSON DSL Rule Engine Code-based Strategy

và chọn phương án phù hợp.

------------------------------------------------------------------------

# 78. SIGNAL EXPLANATION

Mỗi signal phải lưu evidence.

Ví dụ:

BUY FPT

Reasons:

EMA20 \> EMA50 RSI 63 MACD bullish M15 bullish H1 bullish Volume +42%
Breakout resistance

Không chỉ lưu:

score = 87.

------------------------------------------------------------------------

# 79. SIGNAL VERSIONING

Nếu strategy thay đổi:

signal phải ghi:

strategy_version

indicator_version

model_version

rule_version

------------------------------------------------------------------------

# 80. AI EXPLANATION

AI phải đọc:

signal evidence

thay vì tự suy luận dữ liệu.

Ví dụ:

Input:

FPT score 87 RSI 63 MACD bullish

AI:

"FPT đang có cấu trúc bullish vì..."

Không được tự tạo số liệu.

------------------------------------------------------------------------

# 81. FRONTEND TECH STACK

Antigravity hãy đề xuất stack.

Ưu tiên xem xét:

Next.js React TypeScript Tailwind shadcn/ui

Nhưng không được mặc định nếu repository hiện tại đã có stack khác.

------------------------------------------------------------------------

# 82. BACKEND TECH STACK --- SEE V2.0-028 AND V2.0-029

Ưu tiên xem xét:

Node.js TypeScript Fastify/NestJS

TradingView adapter có thể giữ:

Node.js/TypeScript.

Phải đánh giá:

Python có phù hợp cho quant/backtest không.

Có thể:

Node.js: API + realtime

Python: quant/backtest/ML

------------------------------------------------------------------------

# 83. QUEUE / EVENT BUS --- SEE V2.0-030

Phân tích:

Kafka Redpanda NATS RabbitMQ

Không được chọn chỉ vì phổ biến.

Chọn dựa trên:

throughput latency operability deployment complexity replay ordering
cost

------------------------------------------------------------------------

# 84. DEPLOYMENT

Phải chuẩn bị:

Docker

Local:

docker-compose

Production:

AWS

Có thể xem xét:

ECS EKS RDS ElastiCache MSK

Nhưng chỉ đề xuất khi workload justify.

------------------------------------------------------------------------

# 85. ENVIRONMENTS

Phải có:

local dev staging production

Không dùng production TradingView credential trong local.

------------------------------------------------------------------------

# 86. CI/CD

Phải có:

lint typecheck unit test integration test build security scan container
scan

Deployment:

dev staging production

Có rollback.

------------------------------------------------------------------------

# 87. DOCUMENTATION

Phải tạo:

docs/ ├── architecture.md ├── tradingview.md ├── protocol.md ├──
market-data.md ├── indicators.md ├── signal-engine.md ├── backtest.md
├── api.md ├── security.md ├── deployment.md ├── observability.md ├──
troubleshooting.md └── adr/

------------------------------------------------------------------------

# 88. ADR

Tạo Architecture Decision Records cho:

ADR-001 Architecture ADR-002 TradingView Adapter ADR-003 Database
ADR-004 Event Bus ADR-005 Cache ADR-006 Indicator Engine ADR-007
Strategy Engine ADR-008 Backtest ADR-009 Authentication ADR-010
Multi-tenancy

------------------------------------------------------------------------

# 89. RISK REGISTER

Tạo:

docs/risk-register.md

Ít nhất:

RISK-001 TradingView private API changes RISK-002 Rate limit RISK-003
Account restriction RISK-004 Data licensing RISK-005 Indicator
permission RISK-006 Realtime disconnect RISK-007 Data gap RISK-008
Memory leak RISK-009 Duplicate signal RISK-010 Backtest bias RISK-011
Overfitting RISK-012 Security RISK-013 Cost explosion RISK-014
Multi-tenant isolation

Mỗi risk:

Probability Impact Severity Mitigation Contingency

------------------------------------------------------------------------

# 90. POC REQUIREMENTS

Trước implementation lớn, tạo POC cho:

POC-001 TradingView realtime POC-002 Historical data POC-003 Built-in
indicator POC-004 Pine indicator POC-005 Multiple studies POC-006
Multi-symbol POC-007 Multi-timeframe POC-008 Reconnect POC-009 Rate
limit POC-010 Replay POC-011 Backtest POC-012 1000 symbols benchmark

Mỗi POC phải có:

Objective Setup Experiment Result Conclusion Risk

------------------------------------------------------------------------

# 91. BENCHMARK

Định nghĩa benchmark:

Symbol count: 10 100 500 1,000 5,000

Timeframe:

M1 M5 M15

Measure:

CPU RAM Network WebSocket connections messages/sec events/sec indicator
latency signal latency storage throughput

------------------------------------------------------------------------

# 92. PERFORMANCE TARGET

Antigravity phải đề xuất target dựa trên benchmark.

Ví dụ:

Market event ingestion: \< 100ms internal processing

Signal calculation: \< 500ms

API p95: \< 300ms

Dashboard realtime update: \< 1s

Nhưng không được coi đây là final target trước khi benchmark.

------------------------------------------------------------------------

# 93. COST MODEL

Phải estimate:

Compute Database Redis Kafka Storage Network AI API Monitoring

Theo:

100 users 1,000 users 10,000 users

------------------------------------------------------------------------

# 94. OBSERVABILITY DASHBOARD

Phải thiết kế dashboard:

System Health TradingView Health Market Data Indicator Engine Signal
Engine Backtest Alerts API Database Queue

------------------------------------------------------------------------

# 95. ADMIN DASHBOARD

Admin phải thấy:

TradingView connections active symbols active subscriptions provider
errors 429 reconnect users usage alerts jobs system health

------------------------------------------------------------------------

# 96. FEATURE FLAGS

Các capability rủi ro phải bật bằng feature flag:

PineIndicators Replay Backtest AI Telegram BrokerExecution

------------------------------------------------------------------------

# 97. CONFIGURATION

Không hard-code:

timeframes symbols indicator parameters score weights risk limits alert
cooldown provider endpoints

Dùng configuration.

------------------------------------------------------------------------

# 98. NO OVERENGINEERING

Không xây tất cả ngay.

Ưu tiên:

Foundation → Data → Indicator → Signal → Backtest → Alert → UI → AI →
SaaS

Mỗi phase phải tạo ra giá trị usable.

------------------------------------------------------------------------

# 99. MVP --- SUPERSEDED BY V2.0-042

MVP bắt buộc phải đạt:

1.  TradingView adapter.
2.  Realtime OHLCV.
3.  Historical OHLCV.
4.  Symbol master.
5.  Redis cache.
6.  PostgreSQL/time-series storage.
7.  EMA.
8.  RSI.
9.  MACD.
10. Ichimoku.
11. MTF.
12. Scanner.
13. Score.
14. Entry.
15. SL.
16. TP.
17. Telegram alert.
18. Basic Web Dashboard.

Không cần:

broker execution billing AI ML

ở MVP.

------------------------------------------------------------------------

# 100. MVP DEMO

Demo scenario:

User mở dashboard.

Chọn:

FPT

Timeframes:

M5 M15 H1 D1

System:

1.  lấy realtime.
2.  lấy candles.
3.  tính indicators.
4.  phân tích MTF.
5.  tính score.
6.  phát hiện setup.
7.  tính Entry.
8.  tính SL.
9.  tính TP1/TP2/TP3.
10. tính R:R.
11. hiển thị signal.
12. gửi Telegram.

------------------------------------------------------------------------

# 101. XAUUSD DEMO

Demo thứ hai:

XAUUSD

Timeframes:

M1 M5 M15 H1

Strategy:

Scalping MTF.

Indicators:

EMA RSI MACD Ichimoku Bollinger ATR

Output:

BUY/SELL Entry SL TP1 TP2 RR Score

------------------------------------------------------------------------

# 102. KHÔNG ĐƯỢC LÀM

Không:

-   hard-code TradingView credentials.
-   hard-code signal.
-   hard-code score.
-   hard-code symbol.
-   hard-code indicator parameters.
-   tự nhận định score = probability.
-   dùng future candle.
-   look-ahead bias.
-   duplicate signals.
-   duplicate alerts.
-   expose private indicator source nếu không được phép.
-   log credentials.
-   bypass security controls.
-   assume TradingView internal endpoint is stable.
-   assume commercial redistribution is permitted.

------------------------------------------------------------------------

# 103. CODING STANDARD

TypeScript ưu tiên.

Strict typing.

ESLint.

Prettier.

Clean Architecture ở mức hợp lý.

SOLID.

Dependency Injection nếu phù hợp.

Không over-abstraction.

Code phải testable.

------------------------------------------------------------------------

# 104. ERROR HANDLING

Không swallow error.

Error phải có:

code message context traceId retryable

Ví dụ:

TV_AUTH_EXPIRED TV_RATE_LIMITED TV_CONNECTION_FAILED TV_SYMBOL_NOT_FOUND
TV_PROTOCOL_ERROR DATA_GAP INDICATOR_ERROR SIGNAL_DUPLICATE

------------------------------------------------------------------------

# 105. API ERROR FORMAT

Chuẩn hóa:

{ error: { code, message, details, traceId } }

------------------------------------------------------------------------

# 106. MIGRATION STRATEGY

Mọi DB migration phải:

versioned repeatable rollback-aware

Không sửa schema production thủ công.

------------------------------------------------------------------------

# 107. RELEASE STRATEGY

Semantic versioning.

Feature flag.

Canary nếu cần.

Rollback.

------------------------------------------------------------------------

# 108. ANTIGRAVITY WORKFLOW

BẮT BUỘC làm theo:

STEP 1 Inspect repository.

STEP 2 Inspect package.json.

STEP 3 Inspect source.

STEP 4 Inspect tests.

STEP 5 Inspect existing docs.

STEP 6 Identify current architecture.

STEP 7 Identify reusable code.

STEP 8 Identify gaps.

STEP 9 Research TradingView-API capability.

STEP 10 Build capability matrix.

STEP 11 Build architecture proposal.

STEP 12 Build risk register.

STEP 13 Build POC list.

STEP 14 Build phase roadmap.

STEP 15 Build task dependency graph.

STEP 16 Build implementation plan.

STEP 17 STOP.

WAIT FOR USER APPROVAL.

------------------------------------------------------------------------

# 109. IMPLEMENTATION PLAN FORMAT

Plan phải có:

## Phase

### Objective

### Business value

### Technical scope

### Components

### Files

### APIs

### Database

### Events

### Tests

### Observability

### Security

### Performance

### Risks

### Dependencies

### Definition of Done

### Estimated complexity

### Blocking issues

------------------------------------------------------------------------

# 110. TASK FORMAT

Mỗi task:

TASK-ID

Title

Description

Dependencies

Files

Implementation steps

Tests

Acceptance criteria

Risk

Definition of Done

------------------------------------------------------------------------

# 111. PRIORITY

Dùng:

P0 = blocker/core P1 = critical P2 = important P3 = later

------------------------------------------------------------------------

# 112. ACCEPTANCE CRITERIA

Mỗi feature phải có acceptance criteria có thể kiểm thử.

Ví dụ:

Given:

FPT M5 stream active

When:

new candle update arrives

Then:

MarketDataGateway emits CANDLE_UPDATE

And:

duplicate candle does not create duplicate event.

------------------------------------------------------------------------

# 113. ANTIGRAVITY PHẢI TẠO CÁC ARTIFACT

Sau discovery phải tạo:

1.  architecture.md
2.  implementation-plan.md
3.  roadmap.md
4.  risk-register.md
5.  tradingview-capability-matrix.md
6.  data-model.md
7.  api-design.md
8.  test-strategy.md
9.  observability.md
10. ADRs

------------------------------------------------------------------------

# 114. CAPABILITY MATRIX --- SUPERSEDED/EXTENDED BY V2.0-003

Phải tạo bảng:

  -------------------------------------------------------------------------------
  Capability        TradingView-API       Source   POC       Production   Phase
                    supports?                      needed?   risk         
  ----------------- --------------------- -------- --------- ------------ -------
  Realtime          ?                     ?        Yes       High         1

  OHLCV             ?                     ?        Yes       Medium       1

  Quote             ?                     ?        Yes       Medium       1

  Built-in          ?                     ?        Yes       Medium       3
  Indicator                                                               

  Pine Indicator    ?                     ?        Yes       High         3

  Invite-only       ?                     ?        Yes       Very High    3
  Indicator                                                               

  Replay            ?                     ?        Yes       High         7

  Backtest          ?                     ?        Yes       Medium       7

  Screener          ?                     ?        Yes       Medium       5

  Drawings          ?                     ?        Yes       High         Later
  -------------------------------------------------------------------------------

Không được điền "Yes" chỉ dựa vào README.

------------------------------------------------------------------------

# 115. FINAL ARCHITECTURE DOCUMENT

Phải có architecture diagram dạng:

TradingView ↓ TradingView Adapter ↓ Connection Manager ↓ Subscription
Manager ↓ Market Data Gateway ↓ Event Bus ↓ Data Store ↓ Indicator
Engine ↓ MTF Engine ↓ Strategy Engine ↓ Signal Engine ↓ Risk Engine ↓
Alert Engine ↓ API ↓ Frontend / Telegram

------------------------------------------------------------------------

# 116. QUAN TRỌNG NHẤT

Không được bắt đầu implementation bằng:

"Let's create the app."

Phải bắt đầu bằng:

"Let's inspect the repository and produce an implementation plan."

Không được tự ý thay đổi architecture sau khi plan đã approved mà không
thông báo.

Nếu phát hiện assumption sai:

STOP → explain → update plan → request approval.

------------------------------------------------------------------------

# 117. EXPECTED FIRST RESPONSE FROM ANTIGRAVITY

Response đầu tiên phải trả lời:

1.  Tôi đã đọc những file nào?
2.  Repository hiện tại là gì?
3.  Architecture hiện tại là gì?
4.  TradingView-API cung cấp được gì?
5.  Những gì chưa xác minh?
6.  Những rủi ro lớn nhất?
7.  Kiến trúc đề xuất?
8.  POC nào cần làm trước?
9.  Roadmap Phase 0 → Phase 12?
10. Dependency graph?
11. MVP scope?
12. Non-MVP scope?
13. Các câu hỏi/blocker?
14. Implementation Plan.

Sau đó:

WAIT FOR APPROVAL.

------------------------------------------------------------------------

# 118. APPROVAL GATE

Chỉ sau khi tôi nói:

"APPROVED --- PROCEED"

mới bắt đầu implementation.

Sau mỗi Phase:

STOP.

Report:

-   completed
-   changed files
-   tests
-   benchmark
-   issues
-   technical debt
-   next phase

Sau đó chờ approval tiếp theo.

------------------------------------------------------------------------

# 119. MỤC TIÊU CUỐI CÙNG

Hệ thống cuối cùng phải trở thành một:

## Production-grade AI Trading Intelligence SaaS

Có khả năng:

TradingView → realtime market data → historical data → indicators → Pine
studies → MTF → market structure → strategy → signal → Entry → SL → TP →
R:R → scoring → backtest → optimization → alert → Telegram → dashboard →
AI explanation → SaaS → multi-tenant

Nhưng phải triển khai theo từng phase, có kiểm thử, có benchmark, có
observability, có security và có khả năng thay thế TradingView provider
trong tương lai.

------------------------------------------------------------------------

# 120. FINAL COMMAND --- SUPERSEDED BY V2.0 FINAL COMMAND

Bây giờ:

DO NOT IMPLEMENT YET.

Hãy:

1.  Inspect toàn bộ repository hiện tại.
2.  Inspect TradingView-API source.
3.  Inspect tests/examples.
4.  Map toàn bộ capability.
5.  Xây Architecture Proposal.
6.  Xây Capability Matrix.
7.  Xây Risk Register.
8.  Xây POC Plan.
9.  Xây Phase Roadmap.
10. Xây Dependency Graph.
11. Xây Implementation Plan chi tiết.
12. Xây Task List.

Sau khi hoàn thành:

STOP AND WAIT FOR MY APPROVAL.

Tôi sẽ review Implementation Plan trước khi cho phép bạn bắt đầu coding.

------------------------------------------------------------------------

# V2.0 --- CHANGE SUMMARY

This version keeps the original 120-section master requirement and adds
a control layer focused on:

-   Provider abstraction and provider independence
-   TradingView private/internal protocol risk
-   24-hour realtime stability POC
-   429/WSS disconnect POC
-   study/session capacity benchmark
-   shared subscription aggregation
-   Vietnam ATO/ATC/lunch/session semantics
-   Node.js/Python boundary and serialization benchmark
-   Telegram queue/rate limiter/outbox
-   CSV/Parquet fallback provider
-   canonical market-data contract
-   signal reproducibility
-   candidate vs validated signal
-   score model versioning
-   backtest execution realism
-   survivorship bias
-   corporate actions
-   historical universe membership
-   live/replay/backtest same-logic principle
-   workload-based scaling
-   cost per active user
-   AI grounding tests
-   tenant isolation tests
-   architecture fitness tests
-   commercial/legal readiness gate
-   assumption register
-   decision log
-   non-functional requirements
-   staged MVP-0 / MVP-1 / MVP-2
-   explicit STOP / WAIT / APPROVAL protocol

**V2.0 is the authoritative pre-implementation requirement.**
