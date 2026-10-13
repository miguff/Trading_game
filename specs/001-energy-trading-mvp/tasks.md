---
description: "Task list for Energy Trading Game - Day 1 MVP"
---

# Tasks: Energy Trading Game - Day 1 MVP

**Updated**: 2026-06-11 (Constitutional Amendment v1.2.0 — Mark-to-Market P&L)
**Input**: `specs/001-energy-trading-mvp/spec.md`, `specs/001-energy-trading-mvp/plan.md`, `specs/001-energy-trading-mvp/data-model.md`, `specs/001-energy-trading-mvp/contracts/http-api.md`, `specs/001-energy-trading-mvp/contracts/websocket-messages.md`

## Phase 1: Project skeleton and local run

**Purpose**: Establish the local Python web app skeleton, static asset delivery, WebSocket support, and in-memory game state.

- [ ] T001 [P] Initialize Python project with FastAPI, Uvicorn, Jinja2, pytest, httpx, and websockets in `requirements.txt` (FR-01, NFR-01, NFR-04, NFR-10; complexity S; demo: dependency install passes)
- [ ] T002 [P] Create `app/main.py` with FastAPI app startup and Uvicorn entrypoint (FR-01, FR-02, NFR-01, NFR-04; complexity S; demo: app starts locally)
- [ ] T003 [P] Add `app/game_state.py` defining in-memory player sessions, round state, and role assignment structures (FR-02, FR-13, NFR-10; complexity M; demo: state object instantiates)
- [ ] T004 [P] Add `app/ws_gateway.py` with WebSocket connection routing and broadcast utilities (FR-05, FR-07, NFR-03, NFR-09; complexity M; demo: WebSocket handshake succeeds)
- [ ] T005 Create `static/`, `templates/`, and `tests/` directories with placeholder files for browser UI and tests (FR-01, NFR-01, NFR-02; complexity S; demo: placeholder files exist)
- [ ] T006 [P] Add `app/player_session.py` with session token generation, player registration, and round-robin role assignment logic (FR-02, FR-04, FR-13; complexity M; demo: 30 simulated joins assign roles in order)

---

## Phase 2: Player join and role assignment [US1]

**Goal**: Allow browser players to join by name and receive Generator/Retailer/Trader roles in round-robin order.

**Independent Test**: Open the join page, submit a name, and verify a player session is created with the correct role assignment and lobby state.

- [ ] T007 [US1] Implement `GET /` join page in `app/main.py` rendering `templates/join.html` with name input (FR-01, FR-02, NFR-01; complexity S; demo: join page loads)
- [ ] T008 [US1] Implement `POST /join` in `app/main.py` to register a player name, assign a role by join order, create session token, and return session info (FR-01, FR-02, FR-04, FR-13; complexity M; demo: join flow returns role)
- [ ] T009 [US1] Add `static/join.js` to submit the join form and store the session token locally (FR-01, FR-02, NFR-01; complexity M; demo: browser join persists token)
- [ ] T010 [US1] Extend `app/game_state.py` to track join order and role cycle for 30+ simultaneous players (FR-04, FR-13, NFR-03; complexity M; demo: 30 simulated joins assign roles in order)
- [ ] T011 [US1] Implement `GET /game` route in `app/main.py` to render `templates/game.html` once a player has joined (FR-01, FR-02, FR-20; complexity M; demo: joined user reaches game screen)
- [ ] T012 [US1] Add player role explanation UI to `static/join.js` and `templates/join.html` (FR-02, FR-20; complexity S; demo: role explanation visible after join)

---

## Phase 3: Admin round control [US2]

**Goal**: Provide a minimal admin route to start rounds, select a scenario, and broadcast round start to clients.

**Independent Test**: Use the admin page to start a round and verify connected players receive round start state and news.

- [ ] T013 [US2] Implement `GET /admin` in `app/main.py` rendering `templates/admin.html` with scenario selection (FR-07, FR-09, FR-23, NFR-01; complexity S; demo: admin page loads)
- [ ] T014 [US2] Add `static/admin.js` to send round start requests for selected scenario over WebSocket or HTTP (FR-07, FR-09, FR-27; complexity M; demo: admin start request sends scenario)
- [ ] T015 [US2] Implement `POST /admin/start-round` in `app/main.py` to validate scenario, start a new round, set timer, and store news hint (FR-07, FR-09, FR-23, FR-24; complexity M; demo: round state starts)
- [ ] T016 [US2] Implement `start_round` broadcast in `app/ws_gateway.py` and `app/game_state.py` so all clients receive `round_started` with round number, scenario, news, start price, duration, and remaining seconds (FR-07, FR-09, FR-23, FR-24, FR-27; complexity M; demo: all sockets receive `round_started`)
- [ ] T017 [US2] Add countdown state handling in `app/round_manager.py` and emit remaining seconds every second (FR-24, NFR-03, NFR-09; complexity M; demo: clients see round timer updates)

---

## Phase 4: Market maker and price updates

**Goal**: Implement a game-level stochastic price path with scenario-driven bid/offer updates and no forced final-round endpoint.

**Independent Test**: Start multiple rounds and verify price continuity, scenario bias, stochastic variation, and no forced return to game_start_price.

- [ ] T018 Implement `app/market_maker.py` with configurable spread and scenario-biased stochastic returns, clustered volatility, and occasional jumps (FR-05, FR-06, FR-07, FR-08, NFR-03, NFR-09; complexity M; demo: scenario generator emits varied price points)
- [ ] T019 Implement game-level price history and recent chart point storage in `app/game_state.py` (FR-05, FR-16, NFR-03; complexity M; demo: recent price points are retained across rounds)
- [ ] T020 Add `price_update` broadcast from `app/ws_gateway.py` once per second with bid, offer, last traded price, mid, line_chart_points (30s window), and candle_chart_points (10min, 5s candles) (FR-05, FR-16, NFR-03, NFR-09; complexity M; demo: clients receive `price_update` every second)
- [ ] T021 Ensure `app/market_maker.py` produces a continuous stochastic game-level price path without forcing any round, including the final one, to an endpoint (FR-08; complexity M; demo: final price is generated by market movement)
- [ ] T022 Add `last_traded_price` tracking in `app/game_state.py` and include it in broadcasts (FR-16, FR-19; complexity S; demo: broadcasts include last traded price)

---

## Phase 5: Trading engine [US3]

**Goal**: Execute immediate buy/sell trades at the current market maker price, enforce position limits, and reject invalid trades.

**Independent Test**: Place a buy and sell during an active round and verify server-side execution, position updates, and rejection when inactive or limit exceeded.

- [ ] T023 [US3] Implement `app/trading_engine.py` to execute orders immediately against current offer/bid at quantity 1 MWh (FR-17, FR-18, FR-19, FR-05; complexity M; demo: buy/sell executes with trade record)
- [ ] T024 [US3] Add trade validation in `app/trading_engine.py` to reject orders when no round is active and emit `trade_rejected` (FR-19; complexity S; demo: inactive trade returns error)
- [ ] T025 [US3] Extend `app/game_state.py` with role-specific position limits: Generator 0..+20, Retailer -20..0, Trader -10..+10 (FR-13; complexity M; demo: limit violation is blocked)
- [ ] T026 [US3] Enforce position limit checks in `app/trading_engine.py` before execution and reject invalid trades without state changes (FR-13, FR-19; complexity M; demo: invalid trade rejected)
- [ ] T027 [US3] Update player position and trade history in `app/game_state.py` for each executed order (FR-20, FR-19; complexity M; demo: position and history update after trade)

---

## Phase 6: Profit and loss engine

**Goal**: Calculate live mark-to-market P&L for Generator, Retailer, and Trader, including break-even price, status indicator, unit economics, and round-end close-out with cash reset.

**Independent Test**: Execute sample trades for each role and verify round and cumulative PnL calculations, break-even updates, close-out behavior, and cash reset by role for the next round.

- [X] T028 Implement `app/pnl_engine.py` for Generator PnL: `cost_basis = round_start_price × 0.95`, `expected_cash = -cost_basis × 10`, live PnL = `current_cash + expected_cash + (mid_price × current_position)`, break-even = `-(current_cash + expected_cash) / current_position` (FR-11, FR-20, FR-25; complexity M; demo: generator PnL matches formula)
- [X] T029 Extend `app/pnl_engine.py` for Retailer PnL: `tariff = round_start_price × 1.05`, `expected_cash = +tariff × 10`, live PnL = `current_cash + expected_cash + (mid_price × current_position)`, break-even = `-(current_cash + expected_cash) / current_position` (FR-12, FR-20, FR-25; complexity M; demo: retailer PnL matches formula)
- [X] T030 Extend `app/pnl_engine.py` for Trader PnL: `expected_cash = 0`, live PnL = `current_cash + (mid_price × current_position)`, break-even = `-current_cash / current_position` (FR-14, FR-20, FR-25; complexity M; demo: trader PnL updates correctly)
- [X] T031 Integrate `app/pnl_engine.py` into `app/trading_engine.py` so round PnL, break-even price, and status indicator update after each trade and at close-out (FR-20, FR-25, FR-26; complexity M; demo: PnL updates on trade)
- [X] T032 Implement round-end close-out in `app/round_manager.py`: finalize round PnL using `final_cash + expected_cash + (final_mid_price × final_position)`, add to cumulative PnL, then reset positions and cash by role for next round (FR-25, FR-26, FR-14, FR-20; complexity M; demo: close-out finalizes PnL)

---

## Phase 7: Trading screen

**Goal**: Display live trading state, news, timer, chart, role, position, cash, expected cash, P&L, break-even price, status indicator, and unit economics.

**Independent Test**: Verify the trading screen shows all required metrics updating in real time.

- [X] T033 Implement `templates/game.html` with placeholders for bid, offer, last traded price, news, timer, position (signed MWh), current cash, expected cash, round PnL, cumulative PnL, break-even price, status indicator, unit economics (cost_basis for Generator, tariff for Retailer), and chart canvas (FR-16, FR-20, FR-09, FR-17, FR-18; complexity M; demo: game screen displays placeholders)
- [X] T034 Implement `static/game.js` to render incoming `price_update`, `trade_executed`, and `round_started` events on the page, updating all displayed metrics (FR-16, FR-20, FR-09, NFR-03, NFR-09; complexity M; demo: page updates from socket events)
- [X] T035 Add buy and sell buttons in `templates/game.html` and handle clicks in `static/game.js` to send execute order requests (FR-17, FR-18, FR-19; complexity S; demo: buttons submit trade actions)
- [X] T036 Add break-even price display and status indicator logic in `static/game.js`: show "In profit zone" or "Need price ≥/≤ [value]" based on role and current mid-price (FR-20; complexity M; demo: status indicator updates correctly)
- [X] T037 Add unit economics display in `templates/game.html`: Generator sees `cost_basis` next to expected cash, Retailer sees `tariff` next to expected cash (FR-20; complexity S; demo: unit economics visible)
- [X] T038 Add live chart rendering in `static/game.js` using recent price history and scrolling older points off screen (FR-16; complexity M; demo: chart updates over time)
- [X] T039 Add `static/styles.css` styling for round state, summary visibility, and role labels (FR-20, NFR-02; complexity S; demo: game screen is legible at 1280px)

---

## Phase 8: Round summary and leaderboard [US4]

**Goal**: Broadcast round end, close open positions at final mid-price, display summary and leaderboard, reset positions and cash by role, and allow the next round to start.

**Independent Test**: End a round and verify clients display summary, leaderboard order, position and cash reset by role, and admin can start the next round.

- [ ] T040 [US4] Implement `round_ended` broadcast in `app/ws_gateway.py` with final round PnL, cumulative PnL, and leaderboard data (FR-26, FR-28, NFR-03; complexity M; demo: clients receive `round_ended`)
- [ ] T041 [US4] Implement `app/leaderboard.py` or leaderboard generation in `app/game_state.py` with ranking by cumulative PnL descending, then player name ascending, then join order ascending (FR-28, FR-29; complexity M; demo: leaderboard sort matches tie rule)
- [ ] T042 [US4] Update `templates/game.html` and `static/game.js` to show round summary and leaderboard between rounds and at game end (FR-26, FR-28, FR-29; complexity M; demo: summary and leaderboard render correctly)
- [ ] T043 [US4] Update admin and game flow to allow the next round to start after round end and keep summary visible until start (FR-23, FR-26, FR-27; complexity S; demo: next round can start from summary state)

---

## Phase 9: Testing and demo readiness

**Purpose**: Validate MVP-required requirements, verify constitutional compliance, and prepare demos.

- [X] T044 Add unit tests in `tests/unit/test_market_maker.py`, `tests/unit/test_trading_engine.py`, `tests/unit/test_pnl_engine.py`, and `tests/unit/test_round_manager.py` covering scenario generation, trade execution, PnL, and close-out (FR-05, FR-06, FR-08, FR-11, FR-12, FR-14, FR-19, FR-25, FR-26, NFR-10; complexity M; demo: `pytest` unit tests pass)
- [ ] T045 Add integration tests in `tests/integration/test_game_flow.py` for join, admin round start, price updates, trading, and round end using FastAPI TestClient and WebSocket simulation (FR-01, FR-02, FR-07, FR-16, FR-17, FR-18, FR-19, FR-25, FR-26, NFR-03; complexity L; demo: integration test flow passes)
- [ ] T046 Add unit tests in `tests/unit/test_player_session.py` covering join flow, round-robin role assignment, and session token validation (FR-02, FR-04, FR-13; complexity M; demo: player session tests pass)
- [ ] T047 Add contract validation tests in `tests/unit/test_contracts.py` verifying HTTP API responses and WebSocket message schemas against `contracts/http-api.md` and `contracts/websocket-messages.md` (NFR-10; complexity M; demo: contract tests pass)
- [ ] T048 Perform a 3-player demo with Generator/Retailer/Trader role assignment and verify game lobby, join, and role cycles (FR-02, FR-04; complexity S; demo: 3-player scenario documented)
- [ ] T049 Perform an invalid trade demo where a trade is submitted during inactive round or beyond position limit and verify rejection messages (FR-19, FR-13; complexity S; demo: rejection validated)
- [ ] T050 Perform a 30-player lightweight check using browser tabs or simulated sessions to verify join acceptance and role cycling (FR-04, NFR-03; complexity M; demo: 30-player check log)
- [ ] T051 Perform a full game loop demo from join through summary and leaderboard with at least one round completed (FR-23, FR-26, FR-28; complexity M; demo: full loop documented)
- [ ] T052 Conduct constitution compliance review in `specs/001-energy-trading-mvp/constitution.md` and `specs/001-energy-trading-mvp/spec.md` to verify implementation follows C-01, C-02, and C-03 principles (C-01, C-02, C-03; complexity S; demo: compliance notes recorded)

---

## Dependencies & Execution Order

- **T001–T006**: Phase 1 setup tasks can start immediately in parallel.
- **T007–T012**: Phase 2 depends on Phase 1 completion and builds the join/role foundation.
- **T013–T017**: Phase 3 depends on Phase 1 completion and can proceed once join state exists.
- **T018–T022**: Phase 4 depends on Phase 1 and Phase 3 round infrastructure and can proceed in parallel with Phase 5 once the round manager scaffold exists.
- **T023–T027**: Phase 5 depends on Phase 3 and Phase 4 price infrastructure.
- **T028–T032**: Phase 6 depends on Phase 5 trading execution and Phase 4 price state.
- **T033–T039**: Phase 7 depends on Phase 3 round start and Phase 4 price updates.
- **T040–T043**: Phase 8 depends on Phase 6 close-out and Phase 7 UI readiness.
- **T044–T052**: Phase 9 can proceed as soon as implementation milestones are available for validation.

## Parallel Opportunities

- Setup tasks `T001`, `T002`, `T003`, `T004`, `T006` can run in parallel.
- Game state, WebSocket, player session, and placeholder artifact creation tasks are parallelizable during Phase 1.
- User flows in Phase 2 and Phase 3 can be developed concurrently by separate team members once the baseline app exists.
- Price engine tasks and trading engine tasks can be developed in parallel after round start scaffolding is available.
- UI rendering tasks in Phase 7 can proceed in parallel with backend PnL engine tasks once socket event contracts are stable.

## Implementation Strategy

1. Complete Phase 1 skeleton and local run support.
2. Build Phase 2 join and role assignment to validate player onboarding.
3. Add Phase 3 admin round control and Phase 4 market maker updates.
4. Implement Phase 5 trading and Phase 6 PnL logic to close the core loop.
5. Finish Phase 7 UI and Phase 8 summary/leaderboard support.
6. Validate with Phase 9 tests and demos before declaring the MVP complete.
