# Testing — Always On

Use:
1. targeted test
2. related unit/integration tests
3. type-check/lint/build
4. POC/benchmark
5. E2E when relevant

Every bug fix should include a regression test when practical.
Never claim a test passed unless it was actually executed.
Never weaken a test to make CI pass.
