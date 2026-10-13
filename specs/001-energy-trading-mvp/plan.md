# Implementation Plan: Energy Trading Game - Day 1 MVP

**Branch**: `feature/enhanced_role_dynamics` | **Date**: 2026-06-11 | **Spec**: `specs/001-energy-trading-mvp/spec.md`

**Input**: Feature specification from `specs/001-energy-trading-mvp/spec.md`

## Summary

Build a local Python monolith that implements the Day 1 MVP for the Energy Trading Game. The first vertical slice will deliver:
- browser join and role assignment
- admin-controlled round start with scenario selection
- news hints at round start
- live WebSocket bid/offer price updates with game-level continuous price path
- immediate 1 MWh buy/sell execution against a market maker
- server-side position validation and live mark-to-market P&L calculation
- break-even price and status indicator
- unit economics display (cost_basis for Generator, tariff for Retailer)
- round-end close-out at the last mid-price
- summary and leaderboard display

**Updated for Constitutional Amendment v1.2.0**: Mark-to-market P&L replaces realized-only P&L. Game-level stochastic price path continues across rounds; no round has a forced end price.

## Technical Context

**Language/Version**: Python 3.11+.

**Primary Dependencies**: FastAPI, Uvicorn, Jinja2 (or plain static HTML), `pytest`, `httpx`, `websockets`/`anyio`.

**Storage**: In-memory Python objects. No persistent database.

**Testing**: `pytest` with FastAPI TestClient and WebSocket integration tests.

**Target Platform**: Localhost browser on laptop with 1280px+ width.

**Project Type**: Web application monolith.

**Performance Goals**: Support 30 simultaneous players with sub-2-second WebSocket updates and responsive UI.

**Constraints**: No cloud deployment, no authentication, no persistent DB, no browser refresh persistence required. Any backend endpoints beyond the core UI pages and WebSocket messages are implementation details only. Support endpoints are allowed only if needed to support the MVP-required browser flow, real-time updates, summary, or leaderboard, and they must not expand MVP scope.

**Scale/Scope**: Local Day 1 MVP, single session, moderate concurrency, minimal UI polish.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- All planned features align to MVP-required requirements only.
- Domain logic is separated from UI.
- Server remains authoritative for roles, prices, trades, position limits, P&L, close-out, and leaderboard.
- No cloud, no auth, no player-to-player trading.
- Mark-to-market P&L used (not realized-only) per Constitutional Amendment v1.2.0.
- Game-level price path uses scenario-biased stochastic returns; no round is forced to a target price.
- Positions carry between rounds; each round adds the role allocation and P&L marks carried inventory incrementally.

## Project Structure

### Documentation (this feature)

```text
specs/001-energy-trading-mvp/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── websocket-messages.md
│   └── http-api.md
├── constitution.md      # Constitutional amendments
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 output
```

### Source Code (repository root)

```text
app/
├── __init__.py
├── main.py
├── game_state.py
├── player_session.py
├── market_maker.py
├── trading_engine.py
├── pnl_engine.py
├── round_manager.py
├── market_signals.py
└── ws_gateway.py

static/
├── join.js
├── game.js
├── admin.js
└── styles.css

templates/
├── join.html
├── game.html
└── admin.html

tests/
└── unit/
    └── test_pnl_engine.py
```

**Structure Decision**: Single Python web application monolith with distinct modules for game state, sessions, market making, trading, P&L, rounds, and WebSocket event routing. Frontend is minimal static JS + HTML.

## Data Model

See full details in `data-model.md`. Summary of key entities:

### Game
- `game_id: str`
- `game_start_price: float` — anchor price set at round 1 start, never changes
- `total_rounds: int` (default 5)
- `round_duration_seconds: int` (default 90)
- `current_round_number: int`
- `is_active: bool`
- `players: dict[str, Player]`
- `price_history: list[PricePoint]` — game-level history across all rounds
- `rounds: list[Round]`

### Player
- `player_id: str`, `name: str`, `role: Literal['Generator','Retailer','Trader']`
- `join_order: int` — for round-robin role assignment
- `session_token: str`, `connected: bool`
- **Per-round state** (reset each round):
  - `current_position: int` — signed MWh, carried between rounds
  - `round_opening_position: int` — carried position before the current round allocation
  - `current_cash: float` — running cash ledger in EUR
  - `expected_cash: float` — fixed obligation/revenue in EUR
  - `round_pnl: float` — live mark-to-market P&L
  - `cost_basis: float | None` — Generator only (€/MWh)
  - `tariff: float | None` — Retailer only (€/MWh)
  - `trades: list[Trade]`
- **Game-level state**:
  - `cumulative_pnl: float` — sum of finalized round P&Ls

### RoleSettings
| Role | start_position | min_position | max_position | cost_factor | tariff_factor | has_expected_cash |
|------|---------------|--------------|--------------|-------------|---------------|-------------------|
| Generator | +10 | 0 | +20 | 0.95 | null | true |
| Retailer | -10 | -20 | 0 | null | 1.05 | true |
| Trader | 0 | -10 | +10 | null | null | false |

**P&L Formulas**:
- All roles: `current_cash + expected_cash + (mid_price × current_position) - (round_start_price × round_opening_position)`

**Break-even**: `-(current_cash + expected_cash - round_start_price × round_opening_position) / current_position` when position ≠ 0

### Round
- `round_number: int`
- `scenario: Literal['up','down','oscillate']`
- `news_event: str`
- `round_start_price: float`
- `round_target_end_price: float`
- `current_mid_price: float`
- `bid_price: float`, `offer_price: float`
- `duration_seconds: int`
- `started_at: datetime | None`, `ends_at: datetime | None`
- `is_active: bool`
- `price_history: list[PricePoint]`

**Price path rules**:
- Round 1: `round_start_price = game_start_price`
- Round N>1: `round_start_price = round(N-1).final_mid_price`
- Round target metadata does not constrain generated prices; final round has no snap-back rule.

### Trade
- `trade_id: str`, `player_id: str`, `round_number: int`
- `direction: Literal['buy','sell']`
- `price: float`, `quantity: int` (always 1)
- `timestamp: datetime`

### PricePoint
- `timestamp: datetime`, `mid: float`, `bid: float`, `offer: float`

### LeaderboardEntry
- `player_id: str`, `name: str`, `role: str`
- `cumulative_pnl: float`, `rank: int`

**Sort order**: cumulative_pnl desc → name asc → join_order asc

### Session Tracking
- `session_token` stored in browser localStorage
- mapped to `player_id` in `player_session`
- refresh may rejoin using token; full persistence not required for MVP

## Event Model

### Client → Server
- `join` - player name submission
- `place_trade` - `{direction:'buy'|'sell'}`
- `start_round` - admin request with scenario selection

### Server → Client
- `join_success`
- `join_failure`
- `round_started`
- `price_update`
- `trade_executed`
- `trade_rejected`
- `round_ended`
- `leaderboard_update`
- `error`

## API Routes

### Public UI
- `GET /` - join page
- `POST /join` - join action, returns role and session token
- `GET /game` - trading interface
- `GET /static/{path}` - frontend assets

### Admin UI
- `GET /admin` - admin control page
- `POST /admin/start-round` - begin a new round with selected scenario

### Support
- `GET /api/session` - optional current player/round state for refresh recovery; available only if needed to support the browser flow.
- `GET /api/leaderboard` - optional leaderboard snapshot; available only if needed to support the leaderboard display.

## WebSocket Messages

### Client → Server
- `{type:'join', payload:{name:'Alice'}}`
- `{type:'place_trade', payload:{direction:'buy'}}`
- `{type:'place_trade', payload:{direction:'sell'}}`
- `{type:'start_round', payload:{scenario:'up'|'down'|'volatile'}}`

### Server → Client
- `{type:'join_success', payload:{player_id, name, role, session_token}}`
- `{type:'round_started', payload:{round_number, scenario, news, start_price, duration_seconds, remaining_seconds}}`
- `{type:'price_update', payload:{bid, offer, last_traded_price, mid, line_chart_points, candle_chart_points}}`
- `{type:'trade_executed', payload:{direction, price, new_position, current_cash, expected_cash, round_pnl, cumulative_pnl, break_even_price, status_indicator, cost_basis?, tariff?, last_traded_price}}`
- `{type:'trade_rejected', payload:{reason}}`
- `{type:'round_ended', payload:{round_number, final_mid_price, round_pnl, cumulative_pnl, leaderboard, is_final_round}}`
- `{type:'leaderboard_update', payload:{leaderboard}}`
- `{type:'error', payload:{message}}`

## Implementation Phases

### Phase 1: Core playable loop
- scaffold Python app and static assets
- implement join, session, and round-robin role assignment
- build admin route and scenario selection
- create round manager with start/stop state and timer
- build market maker price engine for up/down/volatile scenarios
- add WebSocket broadcast for `round_started` and `price_update`
- deliver minimal UI for lobby, game screen, and news display

### Phase 2: Trading and close-out
- implement trading engine with immediate 1 MWh execution
- enforce role-specific position limits server-side
- implement P&L engine for Generator, Retailer, and Trader with mark-to-market
- add trade result and rejection messaging
- implement round-end close-out at the last mid-price
- build round summary and leaderboard UI updates
- add break-even price calculation and status indicator
- add unit economics display (cost_basis for Generator, tariff for Retailer)

### Phase 3: Verification and polish
- surface rejected trade errors clearly in UI
- validate timer countdown and round state sync
- validate break-even price and status indicator updates
- validate unit economics display (cost_basis, tariff)
- add unit and integration tests for domain modules
- test with 30 simultaneous clients or simulated sessions
- ensure spec traceability and constitution compliance

## Testing Strategy

### Unit tests
- `test_market_maker.py` — scenario generation and return-to-start logic
- `test_player_session.py` — join flow and round-robin roles
- `test_trading_engine.py` — buy/sell execution, limit rejection, no-trade when inactive
- `test_pnl_engine.py` — Generator/Retailer P&L and Trader realized profit
- `test_round_manager.py` — start/end behavior and close-out

### Integration tests
- join + admin round start end-to-end via FastAPI TestClient
- WebSocket flow for live prices, trades, and round end
- verify summary and leaderboard updates

### Manual acceptance tests
- 30 players join and receive correct roles
- admin starts round, clients receive news and trading screen
- buy and sell update server-side position and P&L instantly
- round timer expires, open positions close at last mid-price
- summary and leaderboard display correctly
- rejected trades show errors and preserve state

## Risk List

- WebSocket load for 30 clients. Mitigate with lightweight messages and efficient broadcasts.
- Timer/resource drift between server and clients. Mitigate by using server-authoritative remaining seconds.
- Session recovery on refresh. Mitigate with token reuse and simple rejoin fallback.
- Scenario return-to-start generation. Mitigate with deterministic path generation.
- Correct close-out and P&L math. Mitigate with focused unit tests.

## Constitution Compliance Check

- **Spec-first MVP-only**: no deferred or out-of-scope features planned.
- **Playable loop first**: phase 1 delivers the end-to-end game flow.
- **Server-authoritative state**: all game rules are on the backend.
- **Market maker only**: trading engine executes only against the market maker.
- **Position limits and role economics**: server-side enforcement in `trading_engine`.
- **Correct P&L before polish**: separate `pnl_engine` for authoritative calculations.
- **Real-time updates**: WebSocket gateway and price broadcasts.
- **Simple local architecture**: Python monolith, in-memory state, local browser.
- **Domain/UI separation**: dedicated backend modules and minimal frontend.
- **Done means verified**: tests and manual acceptance included.
- **Ambiguity resolution**: FR-08 and 1 MWh per click are explicitly captured.

## Traceability

- **FR-01**: join page and route
- **FR-02**: join form and round-robin assignment in `player_session`
- **FR-04**: WebSocket architecture and in-memory player registry
- **FR-05**: `market_maker` module
- **FR-06**: scenario support in `market_maker`
- **FR-07**: `round_manager` selects scenario before start
- **FR-08**: round generation/close-out ensures mid-price returns to start
- **FR-09**: static news event payload on round start
- **FR-11**: Generator cost and P&L in `pnl_engine`
- **FR-12**: Retailer tariff and P&L in `pnl_engine`
- **FR-13**: position limits enforced in `trading_engine`
- **FR-16**: game UI displays bid/offer/last traded/chart
- **FR-17 / FR-18**: UI buttons and `place_trade` events execute 1 MWh
- **FR-19**: immediate execution flow in `trading_engine`
- **FR-20**: player state update on UI with signed position, cash, expected cash, P&L, break-even, and status indicator
- **FR-23**: configurable rounds in `round_manager`
- **FR-24**: configurable duration timer and countdown
- **FR-25**: round-end event and close-out logic
- **FR-26**: summary view and client display until next round
- **FR-27**: admin route starts rounds manually
- **FR-28**: leaderboard module and ranking UI
- **NFR-01 / NFR-02 / NFR-03 / NFR-04 / NFR-09 / NFR-10**: architecture and deployment plan
