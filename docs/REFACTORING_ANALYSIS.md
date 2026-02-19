# D2trader Codebase Refactoring Analysis

> Generated: 2026-02-19
> Scope: Full codebase analysis (~8,500 lines Python + ~3,500 lines TypeScript)

## 1. Overview

The D2trader codebase is **well-architected overall** with clear layered separation
(core → strategies → execution → API → UI), proper security patterns (no hardcoded
secrets, header-based auth), and excellent documentation. The strategy plugin system,
API proxy chain, and simulation mode are well-designed.

**Main areas needing improvement:**

- **Code duplication** in order execution paths (Python) and error handling (all layers)
- **Component sizing** — one 712-line React component, one 211-line hook file
- **State fragmentation** — three separate position storage implementations
- **Type safety gaps** — ~30% Python type hints, loose TypeScript strategy types
- **Error handling inconsistency** — silent failures, missing guards, generic catch blocks

---

## 2. Specific Issues

### Issue 1: Order Execution Code Duplication
- **Category:** Code Duplication
- **Severity:** HIGH
- **Description:** `executor.py::_execute_buy()` (77 lines) and `engine.py::_execute_buy()` (72 lines) share ~70% identical logic. Same for `_execute_sell()` (~68% overlap). Both implement: price determination → quantity calculation → risk validation → position registration → trade logging → callback invocation.
- **Location:** `src/execution/executor.py`, `src/backtest/engine.py`

### Issue 2: Oversized Strategy Card Component
- **Category:** Structure / Separation of Concerns
- **Severity:** HIGH
- **Description:** `strategy-card.tsx` is 712 lines with 5+ mixed concerns (expand/collapse, read-only view, edit view, pairs editing, code editing, deletion), 8 useState hooks, and ~400 lines of JSX split between two display modes.
- **Location:** `web/components/strategy/strategy-card.tsx`

### Issue 3: Fragmented Position Storage
- **Category:** Architecture / Data Consistency
- **Severity:** HIGH
- **Description:** Three separate position representations exist:
  1. `risk_manager.state.positions` (in-memory list, live mode)
  2. `portfolio_tracker.sim_positions` (SQLite, simulation mode)
  3. `engine.positions` (in-memory dict, backtest)
- **Location:** `src/core/risk_manager.py`, `src/core/portfolio_tracker.py`, `src/backtest/engine.py`

### Issue 4: Silent / Missing Exception Handling
- **Category:** Error Handling
- **Severity:** HIGH
- **Description:** 4 `except Exception: pass` blocks silently swallow errors. Additionally, `pyapi/routers/portfolio.py` has no try-except on any of its 4 endpoints, breaking the consistent error envelope pattern.
- **Location:** `src/core/config.py:83,91`, `src/execution/collector.py:167`, `src/core/risk_manager.py:254`, `pyapi/routers/portfolio.py:16-66`

### Issue 5: Benchmark Router Duplication
- **Category:** Code Duplication
- **Severity:** MEDIUM
- **Description:** `get_benchmark_data()` (74 lines) and `get_benchmark_data_range()` (64 lines) duplicate DB query, yfinance fallback, DataFrame formatting, and response building (~60 lines overlap).
- **Location:** `pyapi/routers/benchmark.py:38-172`

### Issue 6: Overloaded Control Hook
- **Category:** Structure / Single Responsibility
- **Severity:** MEDIUM
- **Description:** `use-control.ts` (211 lines) bundles 5 unrelated hooks: useKillSwitch, useBotExecution, useScheduler, useTradingMode, useLogViewer.
- **Location:** `web/hooks/use-control.ts`

### Issue 7: Frontend Error Handling Boilerplate
- **Category:** Code Duplication
- **Severity:** MEDIUM
- **Description:** 35+ instances of identical error catch pattern. Loading/error state rendering duplicated across 4+ tab containers. 10+ API routes have identical try-catch wrappers.
- **Location:** Multiple components, `web/app/api/*/route.ts`

### Issue 8: Strategy Signal Parameter Variability
- **Category:** Design Pattern
- **Severity:** MEDIUM
- **Description:** Each strategy's `generate_signals()` accepts different parameter shapes. The backtest engine must know each strategy's type via `prepare_signal_kwargs()`, making extension fragile.
- **Location:** `src/strategies/*.py::generate_signals()`, `src/backtest/engine.py`

### Issue 9: Analyzer Summary Monolith
- **Category:** Function Complexity
- **Severity:** MEDIUM
- **Description:** `BacktestAnalyzer.summary()` is 112 lines computing 15+ metrics in a single method. Individual metrics are untestable.
- **Location:** `src/backtest/analyzer.py::summary()`

### Issue 10: Weak TypeScript Strategy Types
- **Category:** Type Safety
- **Severity:** MEDIUM
- **Description:** `StrategyConfig` uses `[key: string]: unknown` index signature, defeating type checking. Multiple `as Record<string, unknown>` type casts in components.
- **Location:** `web/types/strategy.ts`, `web/components/control/execution-status.tsx:71`

### Issue 11: Test Configuration Duplication
- **Category:** Code Duplication
- **Severity:** LOW
- **Description:** ~170 lines (22%) of test_strategies.py is hardcoded config dictionaries. `QUANT_FACTOR_ABS_MOM_CONFIG` is 73% identical to `QUANT_FACTOR_CONFIG`.
- **Location:** `tests/test_strategies.py:18-527`

### Issue 12: RiskManager Sequential Checks
- **Category:** Extensibility
- **Severity:** LOW
- **Description:** `can_open_position()` has 8 sequential risk checks with early returns. Hard to disable/reorder rules or test individual rules.
- **Location:** `src/core/risk_manager.py::can_open_position()`

### Issue 13: Timing Attack in Secret Comparison
- **Category:** Security
- **Severity:** LOW
- **Description:** `deps.py:16` uses `!=` for secret comparison instead of `hmac.compare_digest()`.
- **Location:** `pyapi/deps.py:16`

### Issue 14: Strategy API Calls Bypass api-client
- **Category:** Consistency
- **Severity:** LOW
- **Description:** `strategy-tab.tsx` uses direct `fetch()` for toggle/delete operations instead of `api-client.ts`.
- **Location:** `web/components/strategy/strategy-tab.tsx:25,46`

### Issue 15: Missing Integration Tests
- **Category:** Testing
- **Severity:** LOW
- **Description:** 85 tests cover strategies and simulation well, but no tests for: executor order flow, backtest analyzer accuracy, FastAPI endpoint responses.
- **Location:** `tests/` (missing files)

---

## 3. Refactoring Recommendations

### R1: Unify Order Execution via Adapter Pattern (Issues 1, 3)

**What:** Extract common order execution logic into an `OrderManager` interface with `LiveOrderManager` and `BacktestOrderManager` adapters.

**Why:** Eliminates ~140 lines of duplication and ensures bug fixes apply universally.

**Steps:**
1. Define `OrderManager` protocol in `src/execution/order_manager.py`
2. Implement `LiveOrderManager` (wraps broker + portfolio_tracker)
3. Implement `BacktestOrderManager` (wraps internal dict + cash tracking)
4. Refactor `executor.py` and `engine.py` to delegate to respective adapter

### R2: Break Down strategy-card.tsx (Issue 2)

**What:** Split the 712-line component into 4-5 focused components.

**Steps:**
1. Extract `StrategyCardHeader` (title, enabled toggle, expand button)
2. Extract `StrategyCardDetails` (read-only parameter display, ~150 lines)
3. Extract `StrategyCardEditor` (edit form with save/cancel, ~250 lines)
4. Extract `PairEditor` and `UniverseCodeEditor`
5. Keep `strategy-card.tsx` as thin orchestrator (~80 lines)

### R3: Extract Benchmark Data Helper (Issue 5)

**What:** Create `_fetch_benchmark_data(symbol, start_date, end_date)` shared helper.

**Why:** Eliminates ~60 lines of duplication in benchmark.py.

### R4: Add Error Guards to portfolio.py (Issue 4)

**What:** Wrap all 4 portfolio endpoints in try-except with consistent envelope.

### R5: Split use-control.ts (Issue 6)

**What:** Split into 5 separate hook files: `use-kill-switch.ts`, `use-bot-execution.ts`, `use-scheduler.ts`, `use-trading-mode.ts`, `use-log-viewer.ts`.

### R6: Create Shared Error Utilities (Issue 7)

**What:** Create `getErrorMessage()` utility and `<DataLoadState>` wrapper component.

### R7: Fix Silent Exception Handlers (Issue 4)

**What:** Replace 4 `except Exception: pass` blocks with explicit logging.

### R8: Use hmac.compare_digest for Secret Comparison (Issue 13)

**What:** Replace `!=` with `hmac.compare_digest()` in `pyapi/deps.py`.

---

## 4. Priority Order

| Priority | Rec | Effort | Impact | Rationale |
|----------|-----|--------|--------|-----------|
| 1 | R4: Portfolio error guards | Small | High | Quick win — prevents inconsistent 500s |
| 2 | R7: Fix silent exceptions | Small | High | Quick win — improves debuggability |
| 3 | R8: hmac.compare_digest | Tiny | Medium | 1-line security fix |
| 4 | R3: Benchmark helper | Small | Medium | Clean ~60 lines duplication |
| 5 | R6: Error utilities | Medium | High | Reduces boilerplate across frontend |
| 6 | R5: Split use-control.ts | Small | Medium | Clean separation, low risk |
| 7 | R2: Break down strategy-card | Medium | High | Largest component, biggest readability win |
| 8 | R1: Unify order execution | Large | Very High | Highest impact but riskiest — needs thorough testing |

Start with small, low-risk fixes (R4, R7, R8) to build confidence. Then tackle
medium-effort frontend cleanup (R6, R5, R2). Save the largest architectural refactor
(R1) for last since it touches the critical trading path.
