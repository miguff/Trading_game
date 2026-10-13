# WebSocket Message Contracts

**Date**: 2026-06-11
**Spec**: `specs/001-energy-trading-mvp/spec.md`

## Connection

- Endpoint: `ws://localhost:8000/ws`
- Protocol: JSON messages over WebSocket
- Each client maintains one WebSocket connection per session

---

## Client → Server Messages

### `join`

Player name submission to enter the game.

```json
{
  "type": "join",
  "payload": {
    "name": "Alice"
  }
}
```

**Validation**:
- `name` must be non-empty string, max 50 characters
- Rejected if game has already ended

---

### `place_trade`

Execute a buy or sell order immediately against the market maker.

```json
{
  "type": "place_trade",
  "payload": {
    "direction": "buy"
  }
}
```

**Validation**:
- `direction` must be `"buy"` or `"sell"`
- Rejected if no round is currently active
- Rejected if trade would breach role-specific position limits
- Each message executes exactly 1 MWh

---

### `start_round` (Admin only)

Start a new round with optional scenario override.

```json
{
  "type": "start_round",
  "payload": {
    "scenario": "up"
  }
}
```

**Validation**:
- `scenario` must be `"up"`, `"down"`, or `"oscillate"`
- If omitted, system randomly selects a scenario
- Rejected if a round is already active
- Rejected if all configured rounds have completed

---

## Server → Client Messages

### `join_success`

Acknowledges player join and returns assigned role.

```json
{
  "type": "join_success",
  "payload": {
    "player_id": "uuid-string",
    "name": "Alice",
    "role": "Generator",
    "session_token": "token-string"
  }
}
```

---

### `join_failure`

Reject player join request.

```json
{
  "type": "join_failure",
  "payload": {
    "reason": "Name is required"
  }
}
```

---

### `round_started`

Broadcast when a new round begins.

```json
{
  "type": "round_started",
  "payload": {
    "round_number": 1,
    "scenario": "up",
    "news": "Renewable output forecasts suggest tightening supply...",
    "start_price": 50.0,
    "duration_seconds": 90,
    "remaining_seconds": 90
  }
}
```

---

### `price_update`

Broadcast approximately once per second during active rounds.

```json
{
  "type": "price_update",
  "payload": {
    "bid": 49.75,
    "offer": 50.25,
    "last_traded_price": 50.0,
    "mid": 50.0,
    "line_chart_points": [
      {"timestamp": "2026-06-11T10:00:00Z", "mid": 50.0}
    ],
    "candle_chart_points": [
      {"timestamp": "2026-06-11T10:00:00Z", "open": 49.9, "high": 50.1, "low": 49.8, "close": 50.0}
    ]
  }
}
```

**Notes**:
- `line_chart_points`: latest 30 seconds of mid-price (max 30 points at 1-second intervals)
- `candle_chart_points`: latest 10 minutes of 5-second candles (max 120 candles)
- Price history is game-level and continues across rounds

---

### `trade_executed`

Sent to the player who placed the trade.

```json
{
  "type": "trade_executed",
  "payload": {
    "direction": "buy",
    "price": 50.25,
    "new_position": 11,
    "current_cash": -50.25,
    "expected_cash": -475.0,
    "round_pnl": 27.5,
    "cumulative_pnl": 27.5,
    "break_even_price": 47.50,
    "status_indicator": "In profit zone",
    "last_traded_price": 50.25
  }
}
```

**Role-specific fields**:
- Generator: includes `cost_basis` (€/MWh)
- Retailer: includes `tariff` (€/MWh)
- Trader: `expected_cash` is always 0

---

### `trade_rejected`

Sent when a trade cannot be executed.

```json
{
  "type": "trade_rejected",
  "payload": {
    "reason": "No active round"
  }
}
```

**Rejection reasons**:
- `"No active round"` — no round is currently running
- `"Position limit exceeded"` — trade would breach min/max position
- `"Invalid direction"` — direction is not "buy" or "sell"

---

### `round_ended`

Broadcast when the round timer reaches zero.

```json
{
  "type": "round_ended",
  "payload": {
    "round_number": 1,
    "final_mid_price": 52.0,
    "round_pnl": 45.0,
    "cumulative_pnl": 45.0,
    "leaderboard": [
      {
        "player_id": "uuid",
        "name": "Alice",
        "role": "Generator",
        "cumulative_pnl": 45.0,
        "rank": 1
      }
    ],
    "is_final_round": false
  }
}
```

---

### `leaderboard_update`

Sent between rounds and at game end.

```json
{
  "type": "leaderboard_update",
  "payload": {
    "leaderboard": [
      {
        "player_id": "uuid",
        "name": "Alice",
        "role": "Generator",
        "cumulative_pnl": 45.0,
        "rank": 1
      }
    ]
  }
}
```

---

### `error`

General error message.

```json
{
  "type": "error",
  "payload": {
    "message": "Unexpected server error"
  }
}
```

---

## Message Frequency

| Message | Direction | Frequency |
|---------|-----------|-----------|
| `join` | C→S | Once per player |
| `place_trade` | C→S | On player action |
| `start_round` | C→S | On admin action |
| `join_success` | S→C | Once per successful join |
| `join_failure` | S→C | On join rejection |
| `round_started` | S→C | Once per round start (broadcast) |
| `price_update` | S→C | ~1 per second during active round (broadcast) |
| `trade_executed` | S→C | Per successful trade (to trading player) |
| `trade_rejected` | S→C | Per rejected trade (to trading player) |
| `round_ended` | S→C | Once per round end (broadcast) |
| `leaderboard_update` | S→C | After round end, on request |
| `error` | S→C | On unexpected errors |
