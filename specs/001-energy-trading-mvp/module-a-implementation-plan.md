# Module A Implementation Plan: Admin / Game Master Panel

**Feature**: Admin / Game Master Panel  
**Branch**: `001-energy-trading-mvp`  
**Created**: 2026-06-11  
**Status**: Draft  

---

## 1. Technical Context

### Current State
- FastAPI app with existing `/admin` route and basic admin UI
- RoundManager handles start_round, cancel_active_round, end_round
- GameState manages players, rounds, and game-level state
- WebSocketManager broadcasts events to all clients
- No authentication currently implemented (per Day 1 MVP scope)
- No pause/resume functionality exists
- Admin endpoints use `/admin` prefix (not `/api/admin` as specified)

### Target State
- Protected admin panel with PIN authentication
- Pause/resume round controls
- Manual end round capability
- Live player overview with WebSocket or polling updates
- Scenario selection and duration configuration
- All per Module A specification and clarifications

---

## 2. Affected Files

### Backend (Python)
| File | Changes |
|------|---------|
| `app/main.py` | Add `/api/admin/*` endpoints (or update existing `/admin/*`), add auth dependency, add pause/resume/end endpoints, add players endpoint |
| `app/auth.py` | **New** - Admin authentication helper (PIN validation, session token, signed cookie) |
| `app/round_manager.py` | Add `pause_round()`, `resume_round()`, track paused state and remaining_seconds_at_pause |
| `app/game_state.py` | Add `is_paused` flag to RoundState, store `paused_remaining_seconds` |
| `app/admin_api.py` | **New** - Admin API router (optional, if restructuring main.py) |

### Frontend
| File | Changes |
|------|---------|
| `templates/admin.html` | Add login form, pause/resume/end buttons, player overview panel, scenario dropdown, auth-aware UI states |
| `static/admin.js` | Add login/logout flow, pause/resume/end handlers, player overview rendering, polling for updates, auth token handling |
| `static/styles.css` | Add login form styles, pause state indicators, player overview table styles, admin button states |

### Documentation
| File | Changes |
|------|---------|
| `README.md` | Add ADMIN_PIN documentation, default PIN note |
| This plan | Mark sections complete as implemented |

---

## 3. Data Model Changes

### RoundState (app/game_state.py)
```python
@dataclass
class RoundState:
    # ... existing fields ...
    is_paused: bool = False  # NEW
    paused_remaining_seconds: int = 0  # NEW - remaining seconds when paused
    
    def reset(self) -> None:
        # ... existing reset ...
        self.is_paused = False  # NEW
        self.paused_remaining_seconds = 0  # NEW
```

### Player (no changes)
Player already tracks: name, role, position, round_pnl, cumulative_pnl

### Admin Session (app/auth.py)
```python
@dataclass
class AdminSession:
    token: str
    created_at: datetime
    expires_at: datetime
```

---

## 4. API Endpoint Design

### Namespace Strategy
**Decision**: Keep existing `/admin/*` endpoints for backward compatibility. Add new endpoints at `/api/admin/*` per spec, or migrate all to `/api/admin/*`.

**Recommended approach for MVP**: Add new endpoints at `/api/admin/*` per specification, keep existing `/admin/*` working or redirect to new endpoints.

### Endpoint Summary

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/admin/login` | Public | Validate PIN, create admin session |
| POST | `/api/admin/logout` | Required | Invalidate admin session |
| GET | `/api/admin/status` | Required | Game state: round active/paused, timer, scenario |
| GET | `/api/admin/players` | Required | Live player overview list |
| POST | `/api/admin/start-round` | Required | Start next round with scenario/duration |
| POST | `/api/admin/pause-round` | Required | Pause active round |
| POST | `/api/admin/resume-round` | Required | Resume paused round |
| POST | `/api/admin/end-round` | Required | Manually end active/paused round |

### Request/Response Details

#### POST /api/admin/login
```json
// Request
{
  "pin": "1234"
}

// Response (success)
{
  "authenticated": true,
  "token": "admin-session-token",
  "expires_at": "2026-06-11T12:00:00Z"
}

// Response (failure)
{
  "error": "Invalid PIN"
}
HTTP 401
```

#### GET /api/admin/status
```json
// Response
{
  "authenticated": true,
  "round_active": true,
  "round_paused": false,
  "current_round": 2,
  "next_round_number": 3,
  "total_rounds": 5,
  "scenario": "up",
  "duration_seconds": 90,
  "remaining_seconds": 45,
  "game_complete": false
}
```

#### GET /api/admin/players
```json
// Response
{
  "players": [
    {
      "player_id": "...",
      "name": "Alice",
      "role": "Generator",
      "position": 10,
      "round_pnl": 25.50,
      "cumulative_pnl": 45.00,
      "connected": true,
      "trade_count": 3
    }
  ],
  "count": 5
}
```

#### POST /api/admin/start-round
```json
// Request
{
  "scenario": "up",
  "duration_seconds": 90,
  "total_rounds": 5
}

// Response
{
  "status": "started",
  "round_number": 3,
  "scenario": "up",
  "duration_seconds": 90
}
```

#### POST /api/admin/pause-round
```json
// Response
{
  "status": "paused",
  "paused_at": "2026-06-11T12:30:00Z",
  "remaining_seconds": 45
}
```

#### POST /api/admin/resume-round
```json
// Response
{
  "status": "resumed",
  "remaining_seconds": 45
}
```

#### POST /api/admin/end-round
```json
// Response
{
  "status": "ended",
  "round_number": 2,
  "close_price": 52.50,
  "finalized": true
}
```

---

## 5. Admin Authentication Approach

### Design Decisions
1. **PIN Source**: Read `ADMIN_PIN` from environment variable
2. **Default PIN**: `1234` (development default, documented)
3. **Session Storage**: In-memory dict (no database)
4. **Session Token**: UUID with expiration (e.g., 8 hours)
5. **Transport**: HTTP-only cookie with signed payload OR Authorization header

### Implementation (app/auth.py)
```python
import os
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict
from fastapi import Request, HTTPException
from fastapi.responses import Response

ADMIN_PIN = os.environ.get("ADMIN_PIN", "1234")
SESSIONS: Dict[str, datetime] = {}  # token -> expires_at
SESSION_DURATION_HOURS = 8

def validate_pin(pin: str) -> bool:
    return pin == ADMIN_PIN

def create_session() -> str:
    token = str(uuid.uuid4())
    expires = datetime.utcnow() + timedelta(hours=SESSION_DURATION_HOURS)
    SESSIONS[token] = expires
    return token, expires

def validate_session(token: Optional[str]) -> bool:
    if not token:
        return False
    expires = SESSIONS.get(token)
    if not expires:
        return False
    if datetime.utcnow() > expires:
        del SESSIONS[token]
        return False
    return True

def require_admin(request: Request):
    token = request.cookies.get("admin_session")
    if not validate_session(token):
        raise HTTPException(status_code=401, detail="Admin authentication required")
    return token

def invalidate_session(token: str):
    SESSIONS.pop(token, None)
```

### FastAPI Dependency
```python
from fastapi import Depends
from app.auth import require_admin

@app.post("/api/admin/start-round")
async def start_round(
    request: Request,
    admin_token: str = Depends(require_admin)
):
    # ... implementation
```

---

## 6. Pause/Resume State Handling

### RoundManager Changes (app/round_manager.py)

```python
class RoundManager:
    # ... existing ...
    
    def pause_round(self) -> dict:
        """Pause the active round."""
        round_state = self.game_state.round_state
        if not round_state.is_active:
            raise RuntimeError("No active round to pause")
        if round_state.is_paused:
            raise RuntimeError("Round is already paused")
        
        round_state.is_paused = True
        round_state.paused_remaining_seconds = self._remaining_seconds(round_state)
        
        # Cancel the round task - we'll recreate on resume
        if self._round_task and not self._round_task.done():
            self._round_task.cancel()
        
        return {
            "status": "paused",
            "paused_at": datetime.utcnow().isoformat(),
            "remaining_seconds": round_state.paused_remaining_seconds
        }
    
    def resume_round(self) -> dict:
        """Resume the paused round."""
        round_state = self.game_state.round_state
        if not round_state.is_active:
            raise RuntimeError("No active round to resume")
        if not round_state.is_paused:
            raise RuntimeError("Round is not paused")
        
        round_state.is_paused = False
        remaining = round_state.paused_remaining_seconds
        
        # Update ends_at to continue from now + remaining seconds
        round_state.ends_at = datetime.utcnow() + timedelta(seconds=remaining)
        
        # Restart the round task with remaining time
        self._round_task = asyncio.create_task(
            self._run_round_with_remaining(remaining)
        )
        
        return {
            "status": "resumed",
            "remaining_seconds": remaining
        }
    
    async def _run_round_with_remaining(self, remaining_seconds: int):
        """Continue round from paused state."""
        # Similar to _run_round but with remaining_seconds instead of full duration
        pass
```

### Pause Effects Implementation

| Effect | Implementation |
|--------|----------------|
| Timer stops | Cancel `_round_task` asyncio task |
| Price updates stop | Task cancellation stops price tick loop |
| Trading rejected | Check `round_state.is_paused` in `/trade` endpoint |
| Clients see paused | Broadcast `round_paused` event via WebSocket |

### Resume Effects Implementation

| Effect | Implementation |
|--------|----------------|
| Timer continues | Restart `_round_task` with `remaining_seconds` |
| Price updates resume | Task runs price tick loop again |
| Trading re-enabled | `is_paused = False` allows trades |
| Clients see active | Broadcast `round_resumed` event via WebSocket |

---

## 7. Manual End-Round Handling

### Implementation
```python
async def end_round_manual(self) -> dict:
    """Manually end the current round."""
    round_state = self.game_state.round_state
    
    if not round_state.is_active:
        raise RuntimeError("No active round to end")
    
    # Use latest mid-price as close price
    close_price = round_state.current_mid_price
    
    # Cancel any running task
    if self._round_task and not self._round_task.done():
        self._round_task.cancel()
    
    # Call existing end_round logic (same as timer expiry)
    await self.end_round()  # This uses close_price internally
    
    return {
        "status": "ended",
        "round_number": round_state.round_number,
        "close_price": close_price,
        "finalized": True
    }
```

### Parity with Timer Expiry
- Same close-out trade creation
- Same P&L finalization
- Same `round_ended` broadcast
- Same leaderboard calculation
- Same position carry-forward and next-round allocation logic

---

## 8. Player Overview Update Mechanism

### Option A: WebSocket (Preferred)
- Use existing WebSocketManager.broadcast
- Add `admin_update` event type with player summary
- Broadcast on: player join, trade, round state change

```python
async def broadcast_admin_update(self):
    players_data = [
        {
            "player_id": p.player_id,
            "name": p.name,
            "role": p.role,
            "position": p.current_position,
            "round_pnl": p.round_pnl,
            "cumulative_pnl": p.cumulative_pnl,
            "connected": p.connected,
            "trade_count": len(p.trade_history)
        }
        for p in self.game_state.players.values()
    ]
    
    await self.ws_manager.broadcast("admin_update", {
        "players": players_data,
        "round_state": {
            "active": self.game_state.round_state.is_active,
            "paused": self.game_state.round_state.is_paused,
            "remaining_seconds": self._remaining_seconds()
        }
    })
```

### Option B: Polling (Fallback)
- If WebSocket admin updates are difficult
- Admin JS polls `GET /api/admin/status` every 1 second
- Player price updates remain WebSocket-driven

**Recommended**: Start with Option B for MVP simplicity, add Option A if time permits.

---

## 9. Frontend Admin UI Layout

### Current admin.html Structure
```html
- Status panel
- Config panel (total rounds, duration, scenario schedule)
- Start Round button
- Restart Game button
```

### Updated admin.html Structure
```html
- Login form (shown when not authenticated)
- Main admin panel (shown when authenticated)
  - Status bar (round state, timer, scenario)
  - Control buttons row
    - Start Round (when between rounds)
    - Pause Round (when active, not paused)
    - Resume Round (when paused)
    - End Round (when active or paused)
    - Restart Game (always available)
  - Configuration panel (between rounds only)
    - Scenario dropdown for next round
    - Duration input (with "can't change during round" message when active)
    - Total rounds (disabled after game starts)
  - Player overview panel
    - Live table: Name | Role | Position | Round P&L | Cumulative P&L | Trades
    - Auto-refresh (WebSocket or polling)
  - Logout button
```

### Admin JS State Machine
```javascript
const ADMIN_STATES = {
  NOT_AUTHENTICATED: 'not_authenticated',
  BETWEEN_ROUNDS: 'between_rounds',
  ROUND_ACTIVE: 'round_active',
  ROUND_PAUSED: 'round_paused',
  GAME_COMPLETE: 'game_complete'
};

function updateUIForState(state) {
  // Show/hide elements based on state
  // Enable/disable buttons
  // Update status text
}
```

---

## 10. Test Strategy

### Unit Tests (Backend)
```python
# Test auth
 test_validate_pin_correct()
 test_validate_pin_incorrect()
 test_session_creation_and_expiration()
 test_require_admin_decorator()

# Test pause/resume
 test_pause_active_round()
 test_pause_already_paused_fails()
 test_pause_no_active_round_fails()
 test_resume_paused_round()
 test_resume_not_paused_fails()
 test_remaining_seconds_preserved_on_pause()

# Test manual end
 test_manual_end_uses_latest_mid_price()
 test_manual_end_same_finalization_as_timer()
 test_manual_end_when_paused()

# Test player overview
 test_admin_players_endpoint_returns_all_fields()
 test_admin_players_updates_after_trade()
```

### Integration Tests
```python
# Full flow tests
 test_admin_login_logout_flow()
 test_start_pause_resume_end_round_flow()
 test_trade_rejected_during_pause()
 test_player_overview_live_updates()
 test_scenario_selection_propagates_to_price_engine()
 test_duration_configuration_before_round()
```

### Manual Tests
1. **Auth**: Login with correct PIN, wrong PIN, session expiration
2. **Pause/Resume**: Start round, pause, verify timer stops, try trade (should fail), resume, verify continues
3. **Manual End**: Start round, manually end, verify same result as timer expiry
4. **Player Overview**: Join players, verify they appear, trade, verify P&L updates
5. **Scenario**: Select up/down/oscillate, verify price behavior matches
6. **Duration**: Change duration before round, verify timer counts from new value

---

## 11. Risk List

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Pause/resume task management is complex | Medium | High | Thorough testing of asyncio task cancellation/recreation |
| Session token security concerns | Low | Medium | Use HTTP-only cookies, short expiration, clear docs about MVP nature |
| WebSocket broadcast conflicts | Low | Medium | Ensure admin broadcasts don't interfere with player price updates |
| Frontend state gets out of sync | Medium | Medium | Add periodic full state refresh, clear error messages |
| Existing /admin/* routes break | Low | High | Keep existing routes working, add new /api/admin/* in parallel |
| Duration input "jumping" issue | Medium | Low | Use userEditedDuration flag pattern already in admin.js |
| Scenario validation edge cases | Low | Low | Validate against {up, down, oscillate}, map volatile -> oscillate |

---

## 12. Traceability to A-01 through A-05

### A-01: Round Controls (start, pause, resume, end)
- **Implementation**: `app/round_manager.py` - `pause_round()`, `resume_round()`, `end_round_manual()`
- **API**: `/api/admin/start-round`, `/api/admin/pause-round`, `/api/admin/resume-round`, `/api/admin/end-round`
- **UI**: `templates/admin.html` - Control buttons with state-dependent visibility
- **Trace**: MA-FR-05, MA-FR-06, MA-FR-07, MA-FR-08, MA-FR-09, MA-FR-19, MA-FR-20

### A-02: Live Player Overview
- **Implementation**: `app/main.py` - `GET /api/admin/players` endpoint
- **Data**: Player name, role, position, round_pnl, cumulative_pnl from `game_state.players`
- **Updates**: Polling every 1 second via `admin.js` (or WebSocket if time permits)
- **UI**: Player table in `templates/admin.html`
- **Trace**: MA-FR-17, MA-FR-18

### A-03: Scenario Selection
- **Implementation**: Existing scenario dropdown in `admin.js` + `app/main.py` start-round validation
- **Mapping**: Add `volatile` -> `oscillate` normalization in API
- **UI**: Dropdown with up/down/oscillate options
- **Trace**: MA-FR-10, MA-FR-11, MA-FR-12

### A-04: Round Duration Adjustment
- **Implementation**: Duration input in `admin.js` + `start-round` endpoint
- **Validation**: Min 10 seconds, default 90, integer only
- **Constraint**: Disable input or show message when round active (MA-FR-16)
- **UI**: Duration field with "not allowed during active round" message
- **Trace**: MA-FR-13, MA-FR-14, MA-FR-15, MA-FR-16

### A-05: Admin Authentication
- **Implementation**: `app/auth.py` - PIN validation, session management
- **PIN**: `ADMIN_PIN` env var with default `1234`
- **Session**: In-memory token with expiration, cookie-based
- **Protection**: `Depends(require_admin)` on all `/api/admin/*` except login
- **UI**: Login form in `templates/admin.html`
- **Trace**: MA-FR-01, MA-FR-02, MA-FR-03, MA-FR-04

---

## 13. Integration Boundary Compliance Check

### Compliant (Within Scope)
- ✅ Add admin API endpoints wrapping existing round lifecycle
- ✅ Add pause/resume state management to RoundManager
- ✅ Add auth layer with signed cookies
- ✅ Add admin UI elements for controls and player overview
- ✅ Use existing WebSocketManager for broadcasts
- ✅ Use existing GameState for player data
- ✅ Minimal CSS additions for admin-specific styling

### Out of Scope (Not Planned)
- ❌ No database-backed admin users (per spec)
- ❌ No OAuth/SSO (per spec)
- ❌ No cloud deployment (per spec)
- ❌ No player-to-player trading (per spec)
- ❌ No real market data (per spec)
- ❌ No complex analytics dashboard (per spec)
- ❌ No rewrite of core trading engine (per spec)
- ❌ No changes to player-facing routes beyond synchronization (per spec)

### Integration Points (Careful Coordination)
- ⚠️ Trading engine must check `is_paused` before executing trades
- ⚠️ Price updates must respect pause state
- ⚠️ Timer display must handle paused remaining seconds
- ⚠️ Round end finalization must be callable from both timer and manual end

---

## 14. Implementation Phases (Suggested Order)

### Phase 1: Authentication (Foundation)
1. Create `app/auth.py` with PIN validation and session management
2. Add `/api/admin/login` and `/api/admin/logout` endpoints
3. Add `require_admin` dependency
4. Update `admin.html` with login form
5. Update `admin.js` with login/logout flow
6. Test: Login with correct/wrong PIN, session expiration

### Phase 2: Pause/Resume Core
1. Add `is_paused` and `paused_remaining_seconds` to RoundState
2. Add `pause_round()` and `resume_round()` to RoundManager
3. Modify `_run_round` to support resuming from paused state
4. Update `/trade` endpoint to reject trades when paused
5. Test: Start, pause, verify timer stops, resume, verify continues

### Phase 3: Manual End Round
1. Add `end_round_manual()` to RoundManager
2. Add `/api/admin/end-round` endpoint
3. Test: Manual end produces same result as timer expiry

### Phase 4: Player Overview
1. Add `/api/admin/players` endpoint
2. Add player table to `admin.html`
3. Add polling in `admin.js` (1 second interval)
4. Test: Players appear, updates when they trade

### Phase 5: UI Integration & Polish
1. Add pause/resume/end buttons to admin UI
2. Add state-dependent button visibility
3. Add scenario compatibility mapping (volatile -> oscillate)
4. Add duration constraint messaging
5. Add CSS for admin-specific elements
6. Full integration test

### Phase 6: Documentation
1. Update README with ADMIN_PIN documentation
2. Document default PIN for development
3. Mark this plan sections complete

---

## 15. Success Criteria Verification

| Success Criterion | Verification Method |
|-------------------|---------------------|
| MA-SC-01: Complete control flow | Manual test: Start → Pause → Resume → Manual End |
| MA-SC-02: Pause stops all activity | Unit test: Timer stops, price stops, trades rejected |
| MA-SC-03: Manual end = timer end | Compare round summaries from both methods |
| MA-SC-04: Live overview shows players | Visual check: Player table updates when players join/trade |
| MA-SC-05: Scenario selection enforced | Unit test: Validate scenario, map volatile |
| MA-SC-06: Duration rules respected | Unit test: Min 10, default 90, validation errors |
| MA-SC-07: All endpoints protected | Unit test: 401 on unauthenticated requests |

---

**End of Implementation Plan**
