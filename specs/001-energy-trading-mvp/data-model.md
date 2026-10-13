# Data Model: Energy Trading Game - Day 1 MVP

**Date**: 2026-06-11
**Spec**: `specs/001-energy-trading-mvp/spec.md`
**Constitution**: `specs/001-energy-trading-mvp/constitution.md`

## Entities

### Game

Represents the entire game session.

| Field | Type | Description |
|-------|------|-------------|
| `game_id` | `str` | Unique session identifier |
| `game_start_price` | `float` | Anchor price set when round 1 starts |
| `total_rounds` | `int` | Configured number of rounds (default 5) |
| `round_duration_seconds` | `int` | Duration per round (default 90) |
| `current_round_number` | `int` | Active round number, 0 if not started |
| `is_active` | `bool` | True if any round is currently running |
| `players` | `dict[str, Player]` | All joined players by player_id |
| `price_history` | `list[PricePoint]` | Game-level price history across all rounds |
| `rounds` | `list[Round]` | Completed and current rounds |

**Validation Rules**:
- `total_rounds` must be ≥ 1
- `round_duration_seconds` must be ≥ 10
- `game_start_price` is set once when round 1 starts and never changes

---

### Player

A participant who enters a name and receives a role.

| Field | Type | Description |
|-------|------|-------------|
| `player_id` | `str` | Unique identifier (UUID) |
| `name` | `str` | Player display name |
| `role` | `Literal['Generator','Retailer','Trader']` | Assigned role |
| `join_order` | `int` | Zero-based join sequence for role assignment |
| `session_token` | `str` | Browser session token for rejoin |
| `connected` | `bool` | WebSocket connection status |

**Round State** (cash, allocation basis, and trades refresh at round start; position carries):

| Field | Type | Description |
|-------|------|-------------|
| `current_position` | `int` | Position in MWh (signed) |
| `round_opening_position` | `int` | Position carried into the round before its new role allocation |
| `current_cash` | `float` | Running cash ledger in EUR |
| `expected_cash` | `float` | Fixed obligation/revenue in EUR |
| `round_pnl` | `float` | Live mark-to-market P&L in EUR |
| `cost_basis` | `float` | Generator only: €/MWh production cost |
| `tariff` | `float` | Retailer only: €/MWh customer tariff |
| `trades` | `list[Trade]` | Trades executed this round |

**Game-Level State** (persists across rounds):

| Field | Type | Description |
|-------|------|-------------|
| `cumulative_pnl` | `float` | Sum of finalized round P&Ls |

**Validation Rules**:
- `name` must be non-empty, max 50 characters
- `role` assigned by `join_order % 3`: 0=Generator, 1=Retailer, 2=Trader
- Position must stay within role-specific band (see RoleSettings)

---

### RoleSettings

Defines starting position, limits, and economics per role.

| Field | Generator | Retailer | Trader |
|-------|-----------|----------|--------|
| `role` | `'Generator'` | `'Retailer'` | `'Trader'` |
| `round allocation` | `+10` | `-10` | `0` |
| `min_position` | `0` | `round_opening_position - 20` | `round_opening_position - 10` |
| `max_position` | `round_opening_position + 20` | `0` | `round_opening_position + 10` |
| `cost_factor` | `0.95` | `null` | `null` |
| `tariff_factor` | `null` | `1.05` | `null` |
| `has_expected_cash` | `true` | `true` | `false` |

**P&L Formulas**:

| Role | Formula |
|------|---------|
- All roles | `current_cash + expected_cash + (current_mid_price × current_position) - (round_start_price × round_opening_position)` |

**Break-Even Price**:
- Formula: `-(current_cash + expected_cash - round_start_price × round_opening_position) / current_position` when `position ≠ 0`
- When `position = 0`: undefined, UI shows "Position flat — P&L locked"

**Status Indicator**:
- Generator: "In profit zone" when `mid_price >= break_even`, else "Need price ≥ [break_even]"
- Retailer: "In profit zone" when `mid_price <= break_even`, else "Need price ≤ [break_even]"
- Trader: "In profit zone" when `(position > 0 and mid >= break_even) or (position < 0 and mid <= break_even)`, else appropriate "Need price..." message

---

### Round

Represents a single trading interval.

| Field | Type | Description |
|-------|------|-------------|
| `round_number` | `int` | 1-based round index |
| `scenario` | `Literal['up','down','oscillate']` | Selected price scenario |
| `news_event` | `str` | Static news hint for this round |
| `round_start_price` | `float` | Mid-price at round start |
| `round_target_end_price` | `float` | Legacy field; no round-end price is enforced |
| `current_mid_price` | `float` | Current mid-price |
| `bid_price` | `float` | Current best bid |
| `offer_price` | `float` | Current best offer |
| `duration_seconds` | `int` | Round duration |
| `started_at` | `datetime \| None` | Round start timestamp |
| `ends_at` | `datetime \| None` | Round end timestamp |
| `is_active` | `bool` | True while timer is running |
| `price_history` | `list[PricePoint]` | Price points this round |

**Validation Rules**:
- Round 1: `round_start_price = game_start_price`
- Round N>1: `round_start_price = round(N-1).final_mid_price`
- No round, including the final round, is forced to a target end price
- Scenario must be one of `up`, `down`, `oscillate`

---

### Trade

A single buy or sell executed immediately against the market maker.

| Field | Type | Description |
|-------|------|-------------|
| `trade_id` | `str` | Unique identifier |
| `player_id` | `str` | Reference to Player |
| `round_number` | `int` | Round in which trade occurred |
| `direction` | `Literal['buy','sell']` | Trade direction |
| `price` | `float` | Execution price (offer for buy, bid for sell) |
| `quantity` | `int` | Always 1 MWh |
| `timestamp` | `datetime` | Execution timestamp |

**Validation Rules**:
- `quantity` is always 1
- `direction` must be `buy` or `sell`
- Trade is rejected if no round is active
- Trade is rejected if it would breach position limits

---

### PricePoint

A timestamped record of market prices.

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | `datetime` | Price sample time |
| `mid` | `float` | Mid-price |
| `bid` | `float` | Best bid |
| `offer` | `float` | Best offer |

**Validation Rules**:
- `bid < offer` always (positive spread)
- All prices > 0

---

### NewsEvent

A static news hint associated with a scenario.

| Field | Type | Description |
|-------|------|-------------|
| `scenario` | `Literal['up','down','oscillate']` | Associated scenario |
| `text` | `str` | News text hint |

**Validation Rules**:
- Text hints at but does not explicitly state price direction
- May include plausible decoy details
- Content is static/hardcoded for MVP

---

### LeaderboardEntry

A ranking record for display.

| Field | Type | Description |
|-------|------|-------------|
| `player_id` | `str` | Reference to Player |
| `name` | `str` | Player display name |
| `role` | `str` | Player role |
| `cumulative_pnl` | `float` | Finalized cumulative P&L |
| `rank` | `int` | Position in standings |

**Sorting Rules**:
1. Primary: `cumulative_pnl` descending
2. Tie-breaker 1: `name` ascending
3. Tie-breaker 2: `join_order` ascending

---

## State Transitions

### Player Join Flow
```
[No Player] → join(name) → [Player: role assigned, lobby state]
```

### Round Lifecycle
```
[Idle] → admin starts round → [Round Active: timer counting, prices updating]
       → timer reaches zero → [Round Ended: close-out, summary, leaderboard]
       → admin starts next round → [Round Active] (repeat)
       → final round ends → [Game Ended: final leaderboard]
```

### Trade Lifecycle
```
[Player Active] → place_trade(direction) → [Validate] → {valid} → [Execute] → [Update P&L] → [Broadcast]
                                           → {invalid} → [Reject] → [Broadcast rejection]
```

### Position Carry (between rounds)
```
[Round End] → finalize incremental P&L → add to cumulative → retain closing position
[Next Round] → add role allocation to carried position → reset cash and trade history → set new expected_cash
[Final Round End] → mark and retain final position in game results
```

## Relationships

```
Game 1--* Player
Game 1--* Round
Game 1--* PricePoint (game-level history)
Round 1--* PricePoint (round-level history)
Player 1--* Trade
Player 1--1 RoleSettings (by role name)
Round 1--1 NewsEvent (by scenario)
```
