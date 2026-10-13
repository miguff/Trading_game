# HTTP API Contracts

**Date**: 2026-06-11
**Spec**: `specs/001-energy-trading-mvp/spec.md`

## Base URL

```
http://localhost:8000
```

---

## Public UI Routes

### `GET /`

Join page. Renders the player entry form.

**Response**: HTML (`templates/join.html`)

---

### `POST /join`

Register a player name and receive role assignment.

**Request**:
```json
{
  "name": "Alice"
}
```

**Response** (200 OK):
```json
{
  "player_id": "uuid-string",
  "name": "Alice",
  "role": "Generator",
  "session_token": "token-string"
}
```

**Response** (400 Bad Request):
```json
{
  "error": "Name is required"
}
```

---

### `GET /game`

Trading interface. Requires valid session.

**Query Parameters**:
- `token` (string, required): Session token from `/join`

**Response** (200 OK): HTML (`templates/game.html`)

**Response** (401 Unauthorized):
```json
{
  "error": "Invalid or missing session token"
}
```

---

### `GET /static/{path}`

Static asset delivery (JS, CSS).

**Response**: Static file content with appropriate MIME type

---

## Admin UI Routes

### `GET /admin`

Admin control page. Renders round control interface.

**Response**: HTML (`templates/admin.html`)

---

### `POST /admin/start-round`

Begin a new round with optional scenario selection.

**Request**:
```json
{
  "scenario": "up"
}
```

**Notes**:
- `scenario` is optional; if omitted, system randomly selects from `{up, down, oscillate}`

**Response** (200 OK):
```json
{
  "round_number": 2,
  "scenario": "up",
  "start_price": 52.0,
  "duration_seconds": 90,
  "news": "Renewable output forecasts suggest tightening supply..."
}
```

**Response** (400 Bad Request):
```json
{
  "error": "Invalid scenario. Must be one of: up, down, oscillate"
}
```

**Response** (409 Conflict):
```json
{
  "error": "A round is already active"
}
```

**Response** (409 Conflict):
```json
{
  "error": "All configured rounds have completed"
}
```

---

## Support Routes

### `GET /api/session`

Retrieve current player and round state for refresh recovery.

**Query Parameters**:
- `token` (string, required): Session token

**Response** (200 OK):
```json
{
  "player": {
    "player_id": "uuid",
    "name": "Alice",
    "role": "Generator",
    "current_position": 10,
    "current_cash": 0,
    "expected_cash": -475.0,
    "round_pnl": 25.0,
    "cumulative_pnl": 25.0
  },
  "round": {
    "round_number": 1,
    "is_active": true,
    "remaining_seconds": 45,
    "scenario": "up"
  }
}
```

**Response** (401 Unauthorized):
```json
{
  "error": "Invalid session token"
}
```

---

### `GET /api/leaderboard`

Leaderboard snapshot.

**Response** (200 OK):
```json
{
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
```

---

## Error Responses

All error responses follow this format:

```json
{
  "error": "Human-readable error message"
}
```

**HTTP Status Codes**:
- `200 OK` — Success
- `400 Bad Request` — Invalid input parameters
- `401 Unauthorized` — Missing or invalid session token
- `409 Conflict` — Invalid state transition (e.g., starting round when one is active)
- `500 Internal Server Error` — Unexpected server error
