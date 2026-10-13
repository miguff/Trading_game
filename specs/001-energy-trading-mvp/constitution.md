# Energy Trading Game - Day 1 MVP Constitution

## Amendment: Stochastic Price Path and Profit & Loss Governance

This amendment supersedes any previous requirement that the final market price return to the game starting price.

## 1. Stochastic Game-Level Price Path

**Principles:**
- Store the original `game_start_price` when round 1 starts.
- Prices evolve as stochastic market returns with scenario bias, clustered volatility, and occasional jumps.
- Price movement is not interpolated to a fixed round endpoint.
- The final round has no special mean-reversion or forced return to `game_start_price`.
- Later rounds may start from the previous round's ending mid-price.
- Positive price and broad safety bounds prevent invalid or runaway values.

---

## 2. Position Carry and Role Allocation

Player positions carry forward between rounds, and each round adds a fresh role allocation.

**Principles:**
- Generator receives +10 MWh at the start of each round.
- Retailer receives -10 MWh at the start of each round.
- Trader receives no allocation at round start.
- The round opening position is the previous closing position plus the new role allocation.
- Cash and trade history reset each round; the position does not.
- The final closing position remains available in the game-end results.
- Position limits move with carried inventory: Generator may trade down to 0 or up to carried position +20; Retailer may trade up to 0 or down to carried position -20; Trader may trade 10 MWh either side of the carried position.

---

## 3. Player-Facing Balanced Profit and Loss

Displayed round profit and loss and leaderboard profit and loss must be game-balanced and incremental versus doing nothing.

**Formulas:**

| Role | Displayed PnL Formula |
|------|----------------------|
| All roles | `current_cash + expected_cash + current_position * mark_price - round_opening_position * round_start_price` |

**Definitions:**
- `current_cash` = sell revenue minus buy cost from current round trades only
- `expected_cash` = cost or revenue associated with this round's fresh Generator or Retailer allocation; zero for Trader
- `round_opening_position` = position carried into the round before the fresh allocation
- `mark_price` = current mid-price during the round; at round end, `mark_price` = last mid-price
- `round_start_price` = the starting mid-price of the current round
- cumulative profit and loss = the sum of finalised round profit and loss values

**Rationale:**
- Doing nothing should produce approximately zero profit and loss if the market returns to the relevant balance price by game end.
- Carried inventory is valued at the round opening price so it is not counted again after the previous round's P&L was finalized.
- The final round marks the remaining position at the final market price and includes that value in cumulative P&L.

---

## 4. Incremental Round Profit and Loss

Round profit and loss must use only current round trades and current round mark prices.

**Principles:**
- Round profit and loss includes current round cashflows and marks the full carried position at current market prices.
- The opening market value of carried inventory is subtracted so prior-round value is not double-counted.
- Round cashflow and round trade trackers reset at the start of each round; position carries forward.
- Finalised round profit and loss is added to cumulative profit and loss exactly once.
- Previous round trades must not affect current round profit and loss.

---

## 5. Multiple-Round Game Flow

The game must support multi-round play with proper state management.

**Principles:**
- The game must run for the configured total number of rounds.
- Default total rounds is 5.
- The game must not end after round 1 unless `total_rounds` is 1.
- After each non-final round, the admin can start the next round.
- After the final configured round, show final leaderboard or game ended state.

---

## Out-of-Scope Exclusions (Permanent)

The following features are explicitly out of scope for Day 1 MVP and remain excluded:

- **No authentication** - Players join by name only; no login system.
- **No persistent database** - All state is in-memory; server restart resets everything.
- **No cloud deployment** - Localhost only.
- **No player-to-player trading** - All trades execute against the market maker.
- **No AI-generated news** - News is static text based on scenario.
- **No optional backlog features** - Stick to core MVP only.
- **No advanced visual polish** - Simple, functional UI only.

---

## Amendment History

| Date | Amendment | Description |
|------|-----------|-------------|
| 2026-06-10 | Price Mean-Reversion & PnL Governance | Corrected price to return to game_start_price only at final round; established balanced PnL formulas; confirmed round isolation principles |
| 2026-10-09 | Stochastic Price Path | Replaced fixed curve and final-price target with scenario-biased stochastic returns; no forced game-start-price return |

---

*This constitution governs all implementation decisions for the Energy Trading Game Day 1 MVP.*
