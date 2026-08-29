# Architecture — Always On

- Keep domain logic provider-agnostic.
- Keep TradingView-specific behavior behind the provider boundary.
- Preserve established Node.js <-> Python contracts.
- Reuse existing abstractions.
- Avoid unrelated refactors.

Every non-trivial change identifies affected modules, contracts, data flow,
failure modes, tests, and rollback path.
