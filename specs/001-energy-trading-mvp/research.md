# Research: Energy Trading Game - Day 1 MVP

**Date**: 2026-06-11
**Feature**: `specs/001-energy-trading-mvp/spec.md`
**Branch**: `feature/enhanced_role_dynamics`

## Clarifications Resolved

### 1. P&L Model: Mark-to-Market (Constitutional Amendment v1.2.0)

**Decision**: Use live mark-to-market P&L instead of realized-only P&L.

**Rationale**: Provides players with immediate feedback on their position value as prices move, making the game more engaging and transparent. The formula `current_cash + expected_cash + (current_mid_price × current_position)` gives a true economic picture at every tick.

**Alternatives considered**: Realized-only P&L (superseded by amendment). Mark-to-market is standard in trading and better aligns with player expectations.

### 2. Generator Economics

**Decision**: Generator `cost_basis = round_start_price × 0.95`. At round start, `current_cash = 0`, `expected_cash = -cost_basis × 10`, `current_position = +10 MWh`.

**Rationale**: Generator has a production cost below market price, creating an inherent profit margin. The expected cash represents the cost obligation for the 10 MWh of production. Initial P&L = `10 × 0.05 × round_start_price` (positive).

**Alternatives considered**: Variable cost basis — rejected for simplicity; fixed cost basis per round is deterministic and easy to explain.

### 3. Retailer Economics

**Decision**: Retailer `tariff = round_start_price × 1.05`. At round start, `current_cash = 0`, `expected_cash = +tariff × 10`, `current_position = -10 MWh`.

**Rationale**: Retailer sells to customers at a markup, creating an inherent profit margin. The expected cash represents revenue from the 10 MWh of customer demand. Initial P&L = `10 × 0.05 × round_start_price` (positive).

**Alternatives considered**: Variable tariff — rejected for simplicity; fixed tariff per round is deterministic.

### 4. Trader Economics

**Decision**: Trader `current_cash = 0`, `expected_cash = 0`, `current_position = 0`. P&L = `current_cash + (mid_price × current_position)`.

**Rationale**: Trader has no baseline obligation or revenue. Profit comes purely from buying low and selling high. This is the simplest model and clearly distinguishes the Trader role.

### 5. Trade Impact on Cash

**Decision**: Buy decreases cash by `offer_price`. Sell increases cash by `bid_price`. Cash is a running ledger.

**Rationale**: This models real market mechanics where buying costs money and selling generates revenue. The cash ledger is separate from P&L; P&L includes mark-to-market valuation of open positions.

**Alternatives considered**: Per-trade realized P&L — rejected because mark-to-market provides better live feedback.

### 6. Round-End Close-Out

**Decision**: Final round P&L = `final_cash + expected_cash + (final_mid_price × final_position)`. This value is added to cumulative P&L. Positions and cash reset by role for the next round.

**Rationale**: Close-out at the final mid-price ensures all open positions are economically valued at round end. Resetting positions and cash each round isolates round performance while cumulative P&L tracks overall game performance.

### 7. Break-Even Price

**Decision**: `break_even = -(current_cash + expected_cash) / current_position` when `position ≠ 0`. When `position = 0`, show "Position flat — P&L locked".

**Rationale**: Break-even tells the player at what price their current position would yield zero P&L. It is a key trading metric. The status indicator compares current mid-price to break-even to show if the player is currently in profit.

### 8. Price Path Continuity

**Decision**: Game-level price path. `game_start_price` is stored at round 1 start. Round 1 starts at that price; each subsequent round starts from the previous close. No round, including the final round, is forced to a target price.

**Rationale**: Creates a continuous market narrative across rounds without an artificial closing-price snap-back.

### 9. Stochastic Scenario Price Process (Updated 2026-10-09)

**Decision**: Each tick uses a geometric random walk: scenario drift plus an independent Gaussian log-return shock. Up and down use small opposing drifts; oscillate has zero drift and higher volatility. Up/down phases may reverse during the walk but close on the directionally correct side of their phase opening price. Clamp prices to broad safety bounds.

**Rationale**: Independent random shocks create irregular price movement without scripted regimes. Scenario drift biases direction without guaranteeing it. Neither round targets nor final-round status force an endpoint.

### 10. Visual Price History

**Decision**: Price history is game-level and persists across rounds. Line chart (30-second window) and candle chart (10-minute window, 5-second candles) do NOT reset between rounds.

**Rationale**: Players can see the full, continuous price journey of the game.

### 11. Position Carry (Updated 2026-10-09)

**Decision**: Positions carry between rounds. Each round adds +10 MWh for Generator, -10 MWh for Retailer, and 0 MWh for Trader. Cash and trade history reset at the next round start. Final open positions are marked at the final market price and retained in the result.

**Incremental P&L**: `current_cash + expected_cash + (mid_price × current_position) - (round_start_price × round_opening_position)`. Subtracting the opening value of carried inventory prevents double-counting value finalized in prior rounds.

## Technology Decisions

### WebSocket vs Server-Sent Events

**Decision**: WebSocket (already in plan).

**Rationale**: Bidirectional communication is needed for both price pushes (server→client) and trade placement (client→server). FastAPI has native WebSocket support.

### In-Memory Storage

**Decision**: In-memory Python objects (already in plan).

**Rationale**: Day 1 MVP constraint. No persistent database required. Simple and fast for local play.

### Frontend Approach

**Decision**: Minimal static JS + HTML with Jinja2 templates (already in plan).

**Rationale**: No build step required. Fast to iterate. Sufficient for functional UI. No React/Vue needed for MVP.

## Open Questions (None Remaining)

All clarifications from the spec have been resolved. The plan is ready for design artifacts.
