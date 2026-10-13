# Feature Specification: Energy Trading Game - Day 1 MVP

**Feature Branch**: `001-energy-trading-mvp`

**Created**: 2026-06-10

**Updated**: 2026-06-11 (Module A Clarifications - Admin panel ambiguities resolved)

**Status**: Draft

**Input**: MVP requirement summary for Energy Trading Game - Day 1 MVP

## Clarifications

### Session 2026-06-10
- **Superseded**: ~~Q: Interpret FR-08 as the mid-price returning to the starting price by the end of each round or by the end of the full game? → A: Interpret FR-08 as the mid-price returning to the starting price by the end of each round.~~
- Q: Does each buy or sell click execute exactly 1 MWh? → A: Yes, each buy or sell click executes exactly 1 MWh.

### Session 2026-06-10 (Constitutional Amendment)
- **Game-level price path**: The price path is continuous across the configured game. Store `game_start_price` when round 1 starts. Each later round starts from the previous round's close. No round has a fixed endpoint, and the final round does not return to `game_start_price` by rule.
- **Round price continuity**: Round 1 `round_start_price` equals `game_start_price`. Round 2 starts from round 1's ending price. Each subsequent round starts from the previous round's ending price. Non-final rounds may end above or below their `round_start_price`.
- **Scenario assignment**: Before each round starts, the system determines a scenario (up, down, or oscillate). Default behavior: random selection. Admin can override any round's scenario. The price engine MUST use admin overrides when set.
- **Price generation**: Each tick applies a scenario-biased stochastic log return, mild mean reversion toward that round's opening price, volatility clustering, and a small probability of a market jump. Broad safety bounds apply; no round or final-game endpoint is forced.
- **Visual price history**: Player line chart (30-second window) and candle chart (10-minute window, 5-second candles) MUST NOT reset between rounds. Charts continue from existing game-level price history across rounds.
- **Position carry**: Positions carry between rounds. Each round adds +10 MWh for Generator, -10 MWh for Retailer, and 0 MWh for Trader; final positions are marked at the game closing price.

### Session 2026-06-11 (Constitutional Amendment v1.2.0 — Mark-to-Market P&L)
- **P&L model**: Round P&L is computed as a live mark-to-market value, not realized-only. The formula is: `current_cash + expected_cash + (current_mid_price × current_position)`.
- **Generator economics**: `cost_basis = round_start_price × 0.95`. At round start, `current_cash = 0`, `expected_cash = -cost_basis × 10` (negative = production cost owed). `current_position = +10 MWh`. Initial P&L = `0 + (-cost_basis × 10) + (mid_price × 10)`. Since `mid_price = round_start_price` at t=0, initial P&L = `10 × (round_start_price - cost_basis)` = `10 × 0.05 × round_start_price`.
- **Retailer economics**: `tariff = round_start_price × 1.05`. At round start, `current_cash = 0`, `expected_cash = +tariff × 10` (positive = revenue from customers). `current_position = -10 MWh`. Initial P&L = `0 + (tariff × 10) + (mid_price × -10)` = `10 × (tariff - round_start_price)` = `10 × 0.05 × round_start_price`.
- **Trader economics**: `current_cash = 0`, `expected_cash = 0`, `current_position = 0`. Initial P&L = 0. Each buy subtracts `offer_price` from cash and adds +1 to position. Each sell adds `bid_price` to cash and subtracts -1 from position. Trader P&L = `current_cash + (mid_price × current_position)`.
- **Trade impact on cash**: Buy = cash decreases by `offer_price`. Sell = cash increases by `bid_price`. Cash is a running ledger, not a per-trade P&L.
- **Round-end close-out**: When the round timer reaches zero, the final round P&L is computed using the final mid-price: `final_cash + expected_cash + (final_mid_price × final_position)`. This value is added to cumulative P&L. Positions then reset by role for the next round.
- **Real-time dashboard**: The player's game screen prominently displays `current_position` (signed MWh) as the primary asset metric, alongside `current_cash`, `expected_cash`, and `current_pnl`. All values update on every trade and every price tick.
- **Unit economics display**: Generator sees `cost_basis` (€/MWh) displayed next to expected cash. Retailer sees `tariff` (€/MWh) displayed next to expected cash. This is the per-MWh fixed price that drives the expected cash line item.
- **Break-even price**: Computed live as `-(current_cash + expected_cash) / current_position` when `current_position ≠ 0`. When `current_position = 0`, break-even is undefined and the UI shows "Position flat — P&L locked". The break-even price updates on every trade.
- **Break-even status indicator**: Displayed next to the break-even price. For Generator: "In profit zone" when `current_mid_price >= break_even_price`, otherwise "Need price ≥ [break_even_price]". For Retailer: "In profit zone" when `current_mid_price <= break_even_price`, otherwise "Need price ≤ [break_even_price]". For Trader: "In profit zone" when `(position > 0 and mid_price >= break_even) or (position < 0 and mid_price <= break_even)`, otherwise the appropriate "Need price..." message.

## Core User Flow

1. A player opens the game URL in a browser and lands on a join screen.
2. The player enters their name and is assigned one of three roles in round-robin order: Generator, Retailer, Trader, then repeat.
3. The player waits for the game master to start a round from the admin route.
4. When the round starts, all clients receive the new round number, selected price scenario, and a news event hint.
5. Live market maker bid and offer prices stream to every connected client over WebSocket.
6. The player may place a buy order at the current offer price or a sell order at the current bid price with a single click.
7. Trades execute immediately against the market maker. Cash, position, and live mark-to-market P&L update instantly. Recent prices appear on live charts. Line chart shows latest 30 seconds; candle chart shows latest 10 minutes with 5-second candles.
8. When the round timer reaches zero, the server finalizes round P&L using the final mid-price (mark-to-market close-out: `final_cash + expected_cash + final_mid_price × final_position`), adds it to cumulative P&L, resets positions by role, and broadcasts a round-ended event.
9. All clients display a round summary (round P&L) and cumulative leaderboard. Charts continue across rounds without reset.
10. The game master starts the next round manually. The next round starts from the previous round's ending price. The game continues until all configured rounds complete, with no forced final-round price target.

## User Scenarios & Testing (mandatory)

### User Story 1 - Player joins and receives a role (Priority: P1)
A new player can open the game in a browser, enter a name, and join without installation or account creation.

**Why this priority**: This story establishes the player entry point and the role assignment needed for gameplay.

**Independent Test**: Open the URL, enter a name, and verify that the player lands in the lobby with the correct assigned role.

**Acceptance Scenarios**:
1. Given the game is running, when a new player opens the game URL and submits a name, then the player is accepted into the session and assigned a role by join order.
2. Given players join in sequence, when the 1st, 2nd, 3rd, and 4th players join, then they receive Generator, Retailer, Trader, and Generator respectively.
3. Given the game is running, when 30 players connect and join, then the system continues to accept players and assigns roles in the correct round-robin cycle.

---

### User Story 2 - Game master starts rounds and players receive news (Priority: P1)
The game master controls round starts, selects a price scenario, and players receive round news and the trading screen.

**Why this priority**: Manual round start is part of the Day 1 MVP flow and ensures the server controls round state.

**Independent Test**: Use the admin route to start a round and verify all clients update to the trading screen with news.

**Acceptance Scenarios**:
1. Given the pre-round lobby, when the game master confirms round start via the admin route, then all clients receive a round started event with the round number and news.
2. Given the round is starting, when the game master selects a scenario, then the server uses that scenario for market maker price generation for the round.
3. Given the round has started, when the player views the game screen, then they see the news hint and the live trading interface.

---

### User Story 3 - Players trade against the market maker (Priority: P1)
Players can place buy and sell orders that execute immediately at the current offer or bid price, and the server updates positions and profit and loss.

**Why this priority**: Trading against the market maker is the core interactive gameplay loop.

**Independent Test**: Place buy and sell trades during an active round and verify immediate execution and updated P&L.

**Acceptance Scenarios**:
1. Given an active round and current prices, when a player clicks buy, then the trade executes immediately at the current offer price, cash decreases by the offer price, position increases by 1 MWh, and live P&L updates using the current mid-price.
2. Given an active round and current prices, when a player clicks sell, then the trade executes immediately at the current bid price, cash increases by the bid price, position decreases by 1 MWh, and live P&L updates using the current mid-price.
3. Given an active round is not running, when a player submits a trade request, then the server rejects it with an error and does not record the trade.
4. Given a player has reached their role-specific position limit, when they attempt an order that would exceed it, then the order is rejected and no state changes.
5. Given a Generator at round start with mid-price 50, when no trades have occurred, then the dashboard prominently shows current position as "+10 MWh", current cash is 0, expected cash is -475 EUR, current P&L is +25 EUR, cost_basis is 47.50 €/MWh, break-even price is 47.50 €/MWh, and the status indicator shows "In profit zone".
6. Given a Generator who has sold 5 MWh at bid 55, when the current mid-price is 55, then the dashboard shows current position as "+5 MWh", current cash is +275 EUR, break-even price is 40.00 €/MWh, and the status indicator shows "In profit zone".
7. Given a Retailer at round start with mid-price 50, when no trades have occurred, then the dashboard prominently shows current position as "-10 MWh", current cash is 0, expected cash is +525 EUR, current P&L is +25 EUR, tariff is 52.50 €/MWh, break-even price is 52.50 €/MWh, and the status indicator shows "In profit zone".
8. Given a Trader at round start, when no trades have occurred, then the dashboard prominently shows current position as "0 MWh", current cash is 0, expected cash is 0, and current P&L is 0.

---

### User Story 4 - Round closes and leaderboard updates (Priority: P1)
When the round timer expires, the server finalizes round results using mark-to-market close-out at the final mid-price, resets positions and cash by role, and shows a leaderboard and summary until the next round starts.

**Why this priority**: This ensures the complete play loop is visible, measurable, and repeatable.

**Independent Test**: Let a round timer expire and verify the summary, mark-to-market P&L finalization at the final mid-price, cumulative totals, position and cash reset, and leaderboard display.

**Acceptance Scenarios**:
1. Given a round is active, when the timer reaches zero, then the server finalizes round P&L using the final mid-price (`final_cash + expected_cash + final_mid_price × final_position`), adds it to cumulative P&L, and resets positions by role.
2. Given the round has ended, when the round summary is displayed, then each client shows round P&L and cumulative P&L.
3. Given the round has ended, when the summary is visible, then the leaderboard ranks players by cumulative profit and loss.
4. Given the game is waiting for the next round, when the game master starts the next round, then the new round starts from the previous round's ending price, charts continue without reset, and all clients return to the trading screen.

### Edge Cases
- What happens when a player attempts a trade while no round is active: server returns an error and the trade is not recorded.
- What happens if a player attempts a trade beyond their role-specific position limit: server rejects it without changing position, history, or P&L.
- How does the system handle round state when the admin starts a round before all players have joined: the round still starts for connected players and can be extended by adding more players in subsequent rounds.

## Requirements (mandatory)

### Functional Requirements
- **FR-01**: The player can join the game by opening a URL in a browser. No installation is required.
- **FR-02**: The player enters their name on a join screen with no password or registration required. The system assigns roles by round-robin as players join: player 1 = Generator, player 2 = Retailer, player 3 = Trader, player 4 = Generator, etc.
- **FR-04**: The game supports a minimum of 30 simultaneous players.
- **FR-05**: The system includes a market maker module that continuously generates bid and offer prices visible to all players.
- **FR-06**: The market maker follows a configurable price trend scenario. Three scenarios are supported: up, down, oscillate. Each scenario controls the shape of price movement within the round while maintaining continuity from round start price to round target end price.
- **FR-07**: Before each round starts, the system determines a scenario. Default: random selection from {up, down, oscillate}. The admin MAY override the scenario for any round. Admin overrides MUST be used by the price engine. The scenario determines the mathematical shape applied to the base price trajectory.
- **FR-08**: The price path is continuous across the configured game. Store `game_start_price` at round 1 start. Round 1 starts at `game_start_price`; each subsequent round starts from the previous round's close. Prices follow a scenario-biased stochastic process and are not forced to round endpoints. The final round does not return to `game_start_price` by rule. The game master configures `total_rounds` (default 5) and `round_duration_seconds` (default 90).
- **FR-09**: News events are displayed at the start of each round. The news text hints at but does not directly state the price direction and includes plausible decoy details. News content may be static and hardcoded.
- **FR-11**: The traded commodity is power/electricity. Trade unit is 1 MWh. Prices are quoted in EUR per MWh. A Generator receives +10 MWh each round in addition to the carried position, with a minimum position of 0 and maximum of `round_opening_position + 20 MWh`. Generator `cost_basis = round_start_price × 0.95`; each round's new allocation has `expected_cash = -cost_basis × 10`. Each buy decreases cash by the offer price and increases position by 1 MWh. Each sell increases cash by the bid price and decreases position by 1 MWh.
- **FR-12**: A Retailer receives -10 MWh of customer demand each round in addition to the carried position, with a maximum position of 0 and minimum of `round_opening_position - 20 MWh`. Retailer `tariff = round_start_price × 1.05`; each round's new demand has `expected_cash = +tariff × 10`. Each buy decreases cash by the offer price and increases position by 1 MWh. Each sell increases cash by the bid price and decreases position by 1 MWh.
- **FR-13**: Positions carry across rounds. At round start, `current_position = round_opening_position + role_allocation`, where role allocation is +10 MWh for Generator, -10 MWh for Retailer, and 0 MWh for Trader. Trader's position limits are `round_opening_position ± 10 MWh`. Orders outside the role-specific limits are rejected.
- **FR-14**: Trader receives no new position allocation and carries any open position into the next round. Trader `expected_cash = 0`. Each buy decreases cash by the offer price and increases position by 1 MWh. Each sell increases cash by the bid price and decreases position by 1 MWh.
- **FR-16**: The main game screen displays current best bid price, current best offer price, last traded price, and live price charts. Line chart shows latest 30 seconds of mid-price. Candle chart shows latest 10 minutes using 5-second candles (max 120 candles). Price history is game-level and continues across rounds without reset.
- **FR-17**: The player can place a buy order at the current offer price with a single click or tap. Each buy click executes exactly 1 MWh.
- **FR-18**: The player can place a sell order at the current bid price with a single click or tap. Each sell click executes exactly 1 MWh.
- **FR-19**: Each trade executes immediately against the market maker at the displayed price. There is no order queue. If a trade request is received when no round is active, the server returns an error and no trade is recorded.
- **FR-20**: The player's game screen always prominently displays the current asset position in MWh for all roles, including carried positions plus new allocations. Also displayed: current cash, expected cash, current round P&L, and break-even with a status indicator. Break-even price = `-(current_cash + expected_cash - round_start_price × round_opening_position) / current_position` when position ≠ 0; when position = 0, the UI shows "Position flat — P&L locked".
- **FR-23**: The game consists of a configurable number of rounds with a default of 5. The game must not end after round 1 unless total rounds is set to 1.
- **FR-24**: Each round has a configurable duration timer with a default of 90 seconds. The timer is visible as a countdown on all screens.
- **FR-25**: When the round timer reaches zero, the server broadcasts a round ended event. Round P&L finalises as `final_cash + expected_cash + (final_mid_price × final_position) - (round_start_price × round_opening_position)` and adds to cumulative profit and loss. Positions carry into the next round; a fresh role allocation is added when it starts. Cash resets to 0 at the next round start. After the final round, the remaining position is marked at the final market price and retained in the game-end summary.
- **FR-26**: After the round ended event, all clients display a round summary view showing each player's round profit and loss and cumulative total. After each non-final round ends, the game master may start the next round. After the final configured round ends, the final leaderboard or game ended state is displayed.
- **FR-27**: The game master starts each round manually via an admin route. On confirmation, the server broadcasts a round started event with the new round number and news event. All clients return to the trading screen.
- **FR-28**: A leaderboard screen shows all players ranked by cumulative profit and loss. It is visible between rounds and at game end.
- **FR-29**: The leaderboard ranks players by cumulative profit and loss descending. If players are tied, sort by player name ascending. If names are also tied, sort by join order ascending.

### Non-Functional Requirements
- **NFR-01**: The application is web-based and accessible through a standard browser.
- **NFR-02**: The application must run on a laptop browser with a display of 1280px or wider.
- **NFR-03**: The application must support real-time price updates to all connected clients via WebSocket or Server-Sent Events.
- **NFR-04**: The application must run locally on localhost without cloud deployment for Day 1.
- **NFR-09**: Real-time price updates must be pushed to clients via WebSocket. Polling intervals greater than 2 seconds are not acceptable.
- **NFR-10**: Code is structured so that modules can be extended independently. The market maker, profit and loss engine, and UI are separate concerns.

### Key Entities
- **Game**: Represents the entire game session. Stores `game_start_price` (the anchor price set at the start of round 1), `total_rounds` configuration, and the list of rounds. No round is forced to return to this price.
- **Player**: A participant who enters a name and receives a role. Tracks current cash, expected cash, current position, current round P&L (mark-to-market), cumulative P&L, and display state.
- **Role**: One of Generator, Retailer, or Trader. Defines starting position, allowed position band, economic goal, expected cash formula, and P&L calculation method.
- **MarketMaker**: Generates live bid and offer prices using scenario-biased stochastic returns and pushes updates to connected clients. Round and final-game endpoints are not forced.
- **Round**: Represents a single trading interval with a number, `round_start_price`, duration timer, selected price scenario, news event, and end state. Round 1 `round_start_price` equals `game_start_price`. Each subsequent round starts from the previous round's ending price. No target price is enforced at round end.
- **Trade**: A single buy or sell executed immediately against the market maker at the displayed price. Includes player, timestamp, quantity, price, and direction. Only trades within the current round affect that round's P&L.
- **PricePoint**: A timestamped record of mid-price, bid, and offer used to render the live chart.
- **NewsEvent**: A static or hardcoded round hint associated with the selected scenario.
- **LeaderboardEntry**: A ranking record for a player that includes cumulative profit and loss and position in the standings.

## Success Criteria (mandatory)

### Measurable Outcomes
- **SC-001**: 30 connected players can join and participate without breaking role assignment or game flow.
- **SC-002**: Buy and sell orders execute immediately at the displayed offer or bid price and update player cash, position, and live mark-to-market P&L instantly.
- **SC-003**: The round timer counts down from 90 seconds by default, and the round ends exactly when the timer reaches zero.
- **SC-004**: At round end, round P&L finalises using the final mid-price (mark-to-market close-out), cumulative P&L updates for each player, and positions and cash reset by role for the next round.
- **SC-005**: The leaderboard displays all players ranked by cumulative profit and loss between rounds and at game end.
- **SC-006**: News events appear at round start and provide plausible hints without explicitly stating the direction of prices.
- **SC-007**: Live price updates are pushed to all clients via WebSocket with less than 2 seconds between updates.
- **SC-008**: The price path is continuous across rounds, with each round starting from the previous round's ending price. No round is forced to end at a predetermined price, including the final round.

## Assumptions
- Role assignment is based on the order in which players join the session and is maintained for the duration of the current game session.
- The game runs in-memory for Day 1, and browser refresh persistence is not required unless later marked MVP-required.
- The admin route is local and does not require authentication for Day 1.
- The game master is the session operator who starts rounds manually from the admin route.
- Supporting 30 simultaneously connected players is tested in a local environment using multiple browser sessions or browser tabs.
- The price path is continuous across rounds: round 1 starts at game_start_price, and each subsequent round starts from the previous round's ending price. No final-round snap-back is applied.

## Out of Scope
- Deferred-important items
- Deferred-optional items
- Optional backlog items
- Player-to-player trading
- AI-generated news
- Cloud deployment
- Authentication
- Persistent database
- Visual polish beyond what is needed for playability
- Browser refresh persistence unless explicitly marked MVP-required

## Notes on Ambiguity
- The role assignment order is assumed to be strictly based on join sequence in the current session, with no external registration system.
- News content is assumed to be static and hardcoded for MVP, using the provided sample examples.
- The game master admin route may be a simple local route accessible from the same browser or host, without extra security for Day 1.

---

## Module A Enhancement: Admin / Game Master Panel

### Clarifications (Module A)

#### Session 2026-06-11 (Implementation-Critical Ambiguities Resolved)

The following ambiguities have been resolved with MVP-compatible decisions:

1. **Pause behavior**
   - **Decision**: When admin pauses a round: countdown timer stops, price updates stop, player trades are rejected server-side, clients see paused state. When admin resumes: countdown continues from remaining seconds, price updates resume, trading is allowed again.

2. **Manual end round behavior**
   - **Decision**: Manual end round uses the latest mid-price as close price and runs the same round-end finalisation logic as timer expiry.

3. **Admin authentication**
   - **Decision**: Use a simple admin PIN. Read from environment variable `ADMIN_PIN` if present. If not present, use development default `1234` and document it. Use a simple signed cookie or in-memory admin session token. No database.

4. **Scenario naming**
   - **Decision**: Canonical scenarios are `up`, `down`, `oscillate`. If existing code uses `volatile`, treat `volatile` as alias for `oscillate`.

5. **Round duration**
   - **Decision**: Admin can change duration before starting the next round. Duration cannot be changed while a round is active. Default is 90 seconds. Minimum is 10 seconds.

6. **Admin live overview**
   - **Decision**: Use existing WebSocket broadcast if available. Admin status should update when players join, trade, and rounds change. If WebSocket is difficult, a lightweight GET `/api/admin/status` refresh every 1 second is acceptable for admin only, but player price updates must remain WebSocket-driven.

7. **Integration boundary**
   - **Decision**: Do not rewrite trading engine. Use existing round manager and game state methods. Add admin control methods around existing round lifecycle.

8. **Authorization boundary**
   - **Decision**: All `/api/admin/...` endpoints except login require admin authentication. Unauthenticated requests return 401.

### Feature Overview
Module A adds a dedicated game-master interface and backend controls so an admin can run rounds from the browser, monitor players in near real time, and configure round startup parameters (scenario and duration) without direct server interaction.

### Scope
- Implement all Module A requirements A-01 through A-05.
- A-04 and A-05 are included in scope for this enhancement, even though originally marked SHOULD.

### Integration Boundary
- Frontend route: `/admin`.
- Backend API namespace: `/api/admin/...`.
- Core trading engine behavior must not be rewritten.
- Player-facing routes must not change, except minimal synchronization changes required so player clients reflect admin actions.
- No cloud deployment, no persistent database-backed admin users, no player-to-player trading, and no real market data.

### In-Scope Requirements (A-01 to A-05)
- **A-01 (MUST)**: Game master can start, pause, resume, and end rounds from the admin panel without touching the server directly.
- **A-02 (MUST)**: Admin panel shows a live overview of all players including name, role, position, and current P&L.
- **A-03 (MUST)**: Admin can select the price scenario for the next round before starting it.
- **A-04 (SHOULD, in scope)**: Admin can adjust round duration before starting a round.
- **A-05 (SHOULD, in scope)**: Admin panel is protected by a simple PIN or password.

### Out of Scope (Module A)
- Database-backed admin accounts.
- OAuth, SSO, or enterprise authentication.
- Cloud deployment and cloud secret management.
- Player-to-player trading.
- Real external market data ingestion.
- Complex analytics dashboard beyond the required live overview.
- Rewriting core trading engine behavior unrelated to admin control.
- Changing player-facing routes beyond synchronization needs.

### Functional Requirements (Module A)
- **MA-FR-01 (Admin Route)**: The system MUST expose an admin interface at `/admin`.
- **MA-FR-02 (Auth Required)**: Admin controls and admin data endpoints MUST require admin authentication, except login endpoint.
- **MA-FR-03 (PIN Source)**: Admin PIN MUST be read from `ADMIN_PIN` environment variable when present.
- **MA-FR-04 (PIN Default)**: If `ADMIN_PIN` is not set, system MUST use development default `1234` and document it in startup/README notes.
- **MA-FR-05 (Round Start)**: Admin MUST be able to start the next round when no active round exists and game is not complete.
- **MA-FR-06 (Round Pause)**: Admin MUST be able to pause an active round.
- **MA-FR-07 (Round Resume)**: Admin MUST be able to resume a paused round.
- **MA-FR-08 (Round End Manual)**: Admin MUST be able to manually end an active or paused round.
- **MA-FR-09 (End Finalization Parity)**: Manual end MUST execute the same round-end finalization logic as timer expiry.
- **MA-FR-10 (Scenario Selection)**: Admin MUST choose scenario before starting a round.
- **MA-FR-11 (Scenario Set)**: Supported scenarios MUST be `up`, `down`, and `oscillate`.
- **MA-FR-12 (Scenario Compatibility)**: If internal code uses `volatile`, server MUST map `volatile` to `oscillate` (or accept both consistently).
- **MA-FR-13 (Duration Config)**: Admin MUST be able to set round duration in seconds before starting a round.
- **MA-FR-14 (Duration Defaults/Bounds)**: Default duration MUST be `90` seconds; minimum accepted duration MUST be `10` seconds.
- **MA-FR-15 (Editing Stability)**: Admin duration input MUST NOT reset/jump to 90 while user is actively editing.
- **MA-FR-16 (Active-Round Lock)**: Changing duration while a round is active is not required; UI SHOULD disable input or show a clear message.
- **MA-FR-17 (Live Overview Fields)**: Admin live overview MUST include player name, role, position, current round P&L, and cumulative P&L when available.
- **MA-FR-18 (Live Update Mechanism)**: Admin overview SHOULD use existing WebSocket mechanism if available; otherwise lightweight admin-only status refresh is acceptable.
- **MA-FR-19 (Pause Effects)**: While paused, countdown timer, price updates, and trading MUST stop; trade attempts during pause MUST be rejected server-side.
- **MA-FR-20 (Resume Effects)**: On resume, countdown timer, price updates, and trading MUST continue from paused state.

### Admin Authentication Behavior
- Access to `/admin` requires successful admin login with PIN/password.
- Authentication model is lightweight MVP local auth (no user table, no RBAC).
- Failed login returns a clear, user-visible error.
- Session can be implemented via signed cookie, lightweight server token, or equivalent local mechanism with server-side validation.
- Unauthenticated requests to protected `/api/admin/...` endpoints are rejected with clear unauthorized responses.

### Admin API Expectations (`/api/admin/...`)
Expected endpoint set (exact implementation may include wrappers for backward compatibility):
- `POST /api/admin/login` (public): validate PIN and create admin session.
- `POST /api/admin/logout` (auth required): invalidate admin session.
- `GET /api/admin/status` (auth required): return admin-visible game state including round status, selected/active scenario, timer state, duration, and auth/session status.
- `POST /api/admin/start-round` (auth required): start next round using selected scenario and configured duration.
- `POST /api/admin/pause-round` (auth required): pause active round.
- `POST /api/admin/resume-round` (auth required): resume paused round.
- `POST /api/admin/end-round` (auth required): manually end round using standard round-end finalization.
- `GET /api/admin/players` (auth required): return live player overview data.

Request/response expectations:
- Server validates command preconditions and returns clear errors for invalid state transitions.
- All non-login admin endpoints require authentication.
- `round_started`/status payloads include `duration_seconds` and `remaining_seconds`.

### Round Control Behavior
Start round:
- Allowed only when no round is active and game is not completed.
- Requires selected scenario and chosen/default duration.
- Broadcasts `round_started` to connected clients with scenario and timer fields.

Pause round:
- Allowed only when round is active.
- Paused state freezes countdown and market maker price progression.
- Trading is disabled/rejected server-side during pause.
- Clients receive paused-state update.

Resume round:
- Allowed only when round is paused.
- Resumes countdown and market updates from saved remaining time/state.
- Trading is re-enabled.
- Clients receive active-state update.

End round (manual):
- Allowed when round is active or paused.
- Uses latest available mid-price as close price input.
- Executes standard round-end finalization path (same as timer expiry), including cumulative updates and result broadcasts.

### Live Player Overview Behavior
- Admin view updates near real time for joins, trades, and round state changes.
- Required fields per player row: name, role, position, current round P&L, cumulative P&L (if available).
- Optional additions when already available with low effort: connection status and current round trade count.

### Scenario Selection Behavior
- Admin selects scenario before round start.
- Server stores selected scenario with the round state.
- Price engine uses selected scenario.
- Admin UI shows both selected-next and currently active scenario.
- Supported scenario vocabulary is `up`, `down`, `oscillate`; compatibility mapping for `volatile` is required.

### Round Duration Behavior
- Admin-configurable duration in seconds before round start.
- Default `90`, minimum `10`, integer-only validation server-side.
- UI entry must preserve in-progress editing (no forced reset while typing).
- Active round duration changes are out of scope; input disabled or explicit message is acceptable.
- Start/status payloads include `duration_seconds` and `remaining_seconds` so clients stay synchronized.

### Assumptions (Module A)
- Existing event architecture can broadcast additional admin state transitions without major refactor.
- Existing round manager can accept pause/resume/manual-end commands without rewriting trading core.
- Local MVP deployment context allows simple PIN auth and environment configuration.
- Documentation location for default PIN is available in README/startup notes.

### Edge Cases (Module A)
- Invalid PIN submitted: login denied with clear message; no session created.
- Attempt to access protected endpoint without auth: unauthorized response.
- Start requested while round already active: rejected with state error.
- Pause requested while no active round: rejected.
- Resume requested while not paused: rejected.
- End requested when no active/paused round: rejected.
- Duration below minimum or non-integer: validation error.
- Scenario value outside supported set: validation error.
- Legacy `volatile` scenario submitted: mapped/accepted as `oscillate`.
- Admin UI temporarily disconnected from updates: on reconnect/refresh, `/api/admin/status` provides authoritative state.

### Acceptance Criteria (Given/When/Then)

#### A-01 Round Controls
1. Given no round is active and game is not completed, when authenticated admin starts round, then round enters active state and `round_started` is broadcast.
2. Given a round is active, when authenticated admin pauses round, then timer stops, price updates stop, and trade requests are rejected until resume.
3. Given a round is paused, when authenticated admin resumes round, then timer and price updates continue from paused state and trading resumes.
4. Given a round is active or paused, when authenticated admin manually ends round, then standard round-end finalization runs and `round_ended` is broadcast.

#### A-02 Live Player Overview
1. Given authenticated admin is viewing `/admin`, when players are present, then overview lists each player's name, role, position, and current round P&L.
2. Given cumulative P&L is available, when admin views overview, then cumulative P&L is shown per player.
3. Given a player joins or trades, when update occurs, then admin overview reflects changes in near real time.

#### A-03 Scenario Selection
1. Given admin is preparing next round, when admin selects `up`, `down`, or `oscillate` and starts round, then selected scenario is stored and used by price engine for that round.
2. Given legacy input `volatile`, when submitted for scenario, then system maps/accepts it consistently as `oscillate` behavior.
3. Given round is active, when admin checks panel status, then active scenario is visible.

#### A-04 Round Duration Adjustment
1. Given admin is preparing next round, when admin enters valid integer duration >= 10, then start-round uses that duration.
2. Given no admin change, when round starts, then default duration is 90 seconds.
3. Given admin is typing duration value, when editing field, then UI input does not jump/reset to 90 unexpectedly.
4. Given round is active, when admin attempts duration change, then input is disabled or clear "not allowed during active round" message is shown.

#### A-05 Admin Authentication
1. Given `ADMIN_PIN` is set, when admin logs in with correct PIN, then authenticated session is created.
2. Given `ADMIN_PIN` is not set, when admin logs in with `1234`, then authenticated session is created (development default).
3. Given wrong PIN, when login is attempted, then login fails with clear error and admin controls remain inaccessible.
4. Given unauthenticated request to non-login `/api/admin/...` endpoint, when request is made, then server responds unauthorized.

### Success Criteria (Module A)
- **MA-SC-01**: Admin can complete start, pause, resume, and manual end flow from `/admin` without server console access.
- **MA-SC-02**: During pause, timer, price updates, and trading all stop; after resume, all continue from paused state.
- **MA-SC-03**: Manual end produces the same finalization outputs as timer expiry (round summary, cumulative updates, round end broadcast).
- **MA-SC-04**: Admin live overview shows required player fields and updates near real time.
- **MA-SC-05**: Scenario selection is enforced for each started round with supported scenarios and `volatile` compatibility mapping.
- **MA-SC-06**: Admin duration setting respects default/minimum rules and is propagated to clients in start/status payloads.
- **MA-SC-07**: All `/api/admin/...` endpoints except login are protected by admin authentication.

### Traceability (Module A)
- **A-01** -> MA-FR-05, MA-FR-06, MA-FR-07, MA-FR-08, MA-FR-09, MA-FR-19, MA-FR-20; Acceptance: A-01 scenarios 1-4; Success: MA-SC-01, MA-SC-02, MA-SC-03.
- **A-02** -> MA-FR-17, MA-FR-18; Acceptance: A-02 scenarios 1-3; Success: MA-SC-04.
- **A-03** -> MA-FR-10, MA-FR-11, MA-FR-12; Acceptance: A-03 scenarios 1-3; Success: MA-SC-05.
- **A-04** -> MA-FR-13, MA-FR-14, MA-FR-15, MA-FR-16; Acceptance: A-04 scenarios 1-4; Success: MA-SC-06.
- **A-05** -> MA-FR-01, MA-FR-02, MA-FR-03, MA-FR-04; Acceptance: A-05 scenarios 1-4; Success: MA-SC-07.
