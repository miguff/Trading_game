<!--
Sync Impact Report
Version change: 1.0.0 -> 1.1.0
Amendment: Game-level price path and multi-round behavior
Added principles: VII (Game-level price path), VIII (Round scenarios), IX (Scenario-driven mathematical price function), X (Visual price history), XI (Round accounting)
Principles renumbered: VII through XVI
Rationale: Price mean reversion at final round only supersedes per-round mean reversion
Templates reviewed: .specify/templates/constitution-template.md ✅, .specify/templates/plan-template.md ✅, .specify/templates/spec-template.md ✅
Follow-up TODOs: Update spec.md with game-level price path and scenario behavior
-->

# Energy Trading Game - Day 1 MVP Constitution

## Core Principles

### I. Spec-first and MVP-required-only scope
All implementation MUST be traceable to requirement IDs from the project specification. The Day 1 MVP MUST include only requirements explicitly marked MVP-required. Deferred-important, deferred-optional, and out-of-scope items MUST remain deferred until every MVP-required requirement is implemented and verified. Any new behavior MUST be added to the specification before implementation.

### II. End-to-end playable loop first
The MVP is successful only when the complete game loop works from player join through round summary and leaderboard. The product MUST support browser join by URL, name entry, role assignment, manual round start, news hints, live price updates, buy/sell execution, position/P&L display, automatic round close-out, summary display, leaderboard ranking, and round restart.

### III. Server-authoritative state
The server is the source of truth for player identity, assigned role, game state, round state, selected price scenario, market prices, trades, position limits, profit and loss, round close-out, and leaderboard. Client-side calculations MAY be used only for display convenience and must not determine official results.

### IV. Trading is against the market maker only
For the MVP, all player trading MUST execute against the market maker bot only. Buy orders MUST execute immediately at the current offer price and sell orders MUST execute immediately at the current bid price. There is no order book, no queued orders, and no player-to-player trading.

### V. Position limits and role economics are mandatory
Role-based starting positions, position bands, and profit and loss rules MUST be enforced server-side. Generator starts each round at +10 MWh and may hold 0 to +20 MWh. Retailer starts each round at -10 MWh and may hold -20 to 0 MWh. Trader starts each round at 0 MWh and may hold -10 to +10 MWh. Invalid trades MUST be rejected without changing position, trade history, round profit and loss, or cumulative profit and loss.

### VI. Correct profit and loss before polish
Trading and profit and loss calculation is core game logic. Generator, Retailer, and Trader P&L calculations MUST follow the generated specification. Round-end close-out MUST finalize open positions consistently. Cumulative profit and loss and leaderboard ranking MUST be based on server-calculated values. Correct game economics take priority over visual polish.

### VII. Game-level price path
The market price path is continuous across the configured game. When round 1 starts, the system MUST store game_start_price. The price path MUST start at game_start_price and continue across rounds. Non-final rounds MAY end above or below their round_start_price. The next round MUST start from the previous round's ending price. Only the final tick of the final configured round MUST return exactly to game_start_price.

### VIII. Round scenarios
The game has a configured number of rounds. Before each round starts, the system MUST determine a scenario. Supported scenarios are: up, down, oscillate. By default, the system randomly chooses a scenario for each round. The admin MAY overwrite the randomly chosen scenario for any round. Admin scenario overrides MUST be used by the price engine.

### IX. Scenario-driven mathematical price function
Each round's price movement MUST be continuous from that round's start price to that round's target end price. The round scenario controls the shape of movement inside the round: up scenario SHOULD tend upward, down scenario SHOULD tend downward, oscillate scenario SHOULD move up and down. The final configured round MUST end at game_start_price.

### X. Visual price history
The player line chart and candle chart MUST NOT reset between rounds. Price history is game-level visual history. When the admin continues to the next round, the graphs MUST continue from the previous price path. The candle chart MAY include prices from previous rounds.

### XI. Round accounting
Round profit and loss resets at the start of each round. Round leaderboard is based only on current round profit and loss. Cumulative profit and loss carries across rounds. Cumulative leaderboard is based on cumulative profit and loss. Player positions reset by role at the start of each round. Price history MUST NOT reset when positions and round profit and loss reset.

### XII. Real-time updates are required
The market maker MUST push live price updates to all connected clients using WebSocket or Server-Sent Events. Polling intervals greater than 2 seconds are not acceptable. All players SHOULD see the same active market state.

### XIII. Simple local Day 1 architecture
The implementation MUST be achievable in 6 to 8 hours by a small team using AI-assisted development. Prefer a local browser-based monolith, in-memory state, minimal browser UI, simple admin route, and no cloud dependency. Avoid unnecessary databases, authentication, microservices, complex deployment, or advanced infrastructure.

### XIV. Separate domain logic from UI
Market maker logic, trading validation, profit and loss calculation, round management, and UI rendering MUST be separate concerns. The UI MUST not contain core trading or profit and loss business rules.

### XV. Done means verified
An MVP-required requirement is complete only when it is implemented, linked to its requirement ID, has acceptance criteria satisfied, works in the integrated game flow, and can be manually demonstrated or automatically tested. Code existing in isolation is not enough.

### XVI. Ambiguity resolution
If the generated specification contains ambiguity, choose the simplest interpretation that supports a playable MVP within the Day 1 timebox. If there is a conflict between optional polish and core playability, core playability wins. If a conflict cannot be resolved safely, update the specification before implementation.

## Additional Constraints
The project is a browser-based simulated electricity trading game for AI Developer Day. The MVP MUST run locally with in-memory state and a simple admin route for manual round starts. No browser refresh persistence is required unless explicitly marked MVP-required. The price chart only needs to support recent live price display and does not require overengineered visuals.

## Development Workflow
All Day 1 work MUST follow the constitution principles and remain scoped to MVP-required features. Development SHOULD begin with the specification, proceed through a minimal implementation, and finish with integrated verification of the full game loop. Manual demonstration or automated test evidence MUST exist for each completed MVP-required requirement.

## Governance
This constitution governs Day 1 MVP scope, architecture, and verification for the Energy Trading Game. Amendments require an updated constitution document and a clear rationale for any change. Any new or changed feature definitions MUST be reflected in the project specification before implementation begins.

**Version**: 1.1.0 | **Ratified**: 2026-06-10 | **Last Amended**: 2026-06-10 | **Amendment**: Game-level price path and multi-round behavior
