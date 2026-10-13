# Module A: Task List

**Feature**: Admin / Game Master Panel  
**Created**: 2026-06-11  
**Status**: Ready for implementation  

---

## Legend

- **Req IDs**: A-01 (Round Controls), A-02 (Live Player Overview), A-03 (Scenario Selection), A-04 (Duration Adjustment), A-05 (Admin Authentication)
- **Complexity**: S (Small, <2h), M (Medium, 2-4h), L (Large, 4-8h)
- **Parallelizable**: Yes = can be worked on independently, No = depends on other tasks

---

## Phase 1: Admin Authentication

| ID | Title | Req IDs | Dependencies | Acceptance Criteria | Test Evidence | Parallel | Complexity |
|----|-------|---------|--------------|---------------------|---------------|----------|------------|
| A-TASK-001 | Add admin PIN configuration | A-05 | None | Read `ADMIN_PIN` from env; default to `1234`; log warning on default | Server start with/without env var | Yes | S |
| A-TASK-002 | Create app/auth.py session module | A-05 | 001 | validate_pin(), create_session(), validate_session(), invalidate_session(), require_admin dependency | Unit tests all functions | No | M |
| A-TASK-003 | Add POST /api/admin/login endpoint | A-05 | 002 | Accept `{"pin": "1234"}`; return token+cookie on success; 401 on failure | curl: correct PIN=200, wrong=401 | No | S |
| A-TASK-004 | Add POST /api/admin/logout endpoint | A-05 | 002 | Require auth; invalidate session; clear cookie; return logged_out status | curl: logout then protected=401 | No | S |
| A-TASK-005 | Protect /api/admin/* endpoints | A-05 | 002,003,004 | All endpoints except login use Depends(require_admin); return 401 if not auth | curl: protected endpoints without cookie=401 | No | S |
| A-TASK-006 | Add login form to admin.html | A-05 | 003 | Show form when not auth; PIN input (password type); submit to login; hide on success | Browser: login works, panel shows | Yes | M |
| A-TASK-007 | Handle 401 in admin.js | A-05 | 006 | Detect 401 responses; redirect to login; clear state; show "session expired" message | Browser: expire session, verify redirect | No | S |

---

## Phase 2: Admin API Endpoints

| ID | Title | Req IDs | Dependencies | Acceptance Criteria | Test Evidence | Parallel | Complexity |
|----|-------|---------|--------------|---------------------|---------------|----------|------------|
| A-TASK-008 | Add GET /api/admin/status | A-01,A-02,A-05 | 005 | Require auth; return round_active, round_paused, current_round, scenario, duration, remaining, game_complete | curl: returns full status JSON | No | S |
| A-TASK-009 | Add GET /api/admin/players | A-02 | 005 | Require auth; return array with player_id, name, role, position, round_pnl, cumulative_pnl | curl: with players joined, returns array | No | S |
| A-TASK-010 | Add POST /api/admin/start-round | A-01,A-03,A-04 | 005 | Require auth; accept scenario, duration, total_rounds; validate inputs; reject if active; call round_manager | curl: valid starts, invalid returns 400 | No | M |
| A-TASK-011 | Add POST /api/admin/pause-round | A-01 | 005 | Require auth; reject if not active or already paused; call pause_round(); return paused status | curl: pause active succeeds | No | S |
| A-TASK-012 | Add POST /api/admin/resume-round | A-01 | 005 | Require auth; reject if not paused; call resume_round(); return resumed status | curl: resume paused succeeds | No | S |
| A-TASK-013 | Add POST /api/admin/end-round | A-01 | 005 | Require auth; reject if not active/paused; use latest mid-price; call end_round_manual() | curl: end active succeeds | No | S |

---

## Phase 3: Round Lifecycle Controls

| ID | Title | Req IDs | Dependencies | Acceptance Criteria | Test Evidence | Parallel | Complexity |
|----|-------|---------|--------------|---------------------|---------------|----------|------------|
| A-TASK-014 | Wire start-round to RoundManager | A-01 | 010 | Endpoint calls round_manager.start_round(); handle errors as HTTP 400; broadcast round_started | Integration: start via API, players get WS event | No | S |
| A-TASK-015 | Add pause state to RoundState | A-01 | None | Add is_paused: bool=False; paused_remaining_seconds: int=0; reset both in reset() | Unit: RoundState fields work | Yes | S |
| A-TASK-016 | Implement pause_round() | A-01 | 015 | Calculate/store remaining; set is_paused=True; cancel _round_task; broadcast round_paused | Unit: pause sets state correctly | No | M |
| A-TASK-017 | Implement resume_round() | A-01 | 016 | Set is_paused=False; update ends_at; recreate _round_task; broadcast round_resumed | Unit: resume continues from remaining | No | M |
| A-TASK-018 | Implement end_round_manual() | A-01 | None | Get latest mid-price; set last_traded_price; call existing end_round(); return metadata | Integration: same result as timer | Yes | M |
| A-TASK-019 | Stop timer/price while paused | A-01 | 016,017 | Timer freezes; no price updates; _remaining_seconds() returns paused value when paused | Manual: observe chart, pause, verify no ticks | No | M |
| A-TASK-020 | Reject trades while paused | A-01 | 015 | Check is_paused in /trade endpoint; return 400 "Trading is paused" if paused | Integration: trade during pause rejected | No | S |

---

## Phase 4: Scenario and Duration Controls

| ID | Title | Req IDs | Dependencies | Acceptance Criteria | Test Evidence | Parallel | Complexity |
|----|-------|---------|--------------|---------------------|---------------|----------|------------|
| A-TASK-021 | Add scenario dropdown UI | A-03 | None | Dropdown: Up, Down, Oscillate; store in JS; include in API call; disable when active | Browser: selection works | Yes | S |
| A-TASK-022 | Support up/down/oscillate | A-03 | 010 | Validate scenario in {up,down,oscillate}; return 400 for invalid; pass to MarketMaker | Unit: valid accepted, invalid rejected | No | S |
| A-TASK-023 | Map volatile to oscillate | A-03 | 022 | Accept "volatile"; treat as "oscillate"; log deprecation warning | Unit: volatile=oscillate behavior | No | S |
| A-TASK-024 | Add duration input UI | A-04 | None | Number input; default 90; min 10; include in API; disable with message when active | Browser: input works, constraint shows | Yes | S |
| A-TASK-025 | Validate duration server-side | A-04 | 010 | Validate integer >= 10; return 400 for invalid; use configured duration | curl: 5=400, 90=success | No | S |
| A-TASK-026 | Prevent input jumping | A-04 | 024 | Use userEditedDuration flag; don't overwrite from poll while typing | Browser: type without jumping | No | S |
| A-TASK-027 | Use configured duration | A-04 | 025,026 | Start-round uses request duration; RoundManager uses it; timer counts from value | Integration: 60s round lasts 60s | No | S |

---

## Phase 5: Live Player Overview

| ID | Title | Req IDs | Dependencies | Acceptance Criteria | Test Evidence | Parallel | Complexity |
|----|-------|---------|--------------|---------------------|---------------|----------|------------|
| A-TASK-028 | Display player table UI | A-02 | 009 | Columns: Name, Role, Position, Round P&L, Cumulative P&L; format currency; color codes | Browser: table renders correctly | Yes | S |
| A-TASK-029 | Update on player join | A-02 | 028,008 | Poll /api/admin/players every 1s; update table; show count | Browser: join player, appears in 2s | No | S |
| A-TASK-030 | Update on trade | A-02 | 029 | Position updates; Round P&L updates; Cumulative P&L updates; trade count increments | Browser: trade, verify P&L updates | No | S |
| A-TASK-031 | Update on lifecycle events | A-02 | - | Reset on start; show paused indicator; clear on end | Browser: lifecycle shows correct data | Yes | S |
| A-TASK-032 | Polling mechanism | A-02 | 029 | Poll /api/admin/players and /api/admin/status every 1s; handle errors gracefully | DevTools: verify 1s interval | No | M |

---

## Phase 6: Frontend Admin Panel

| ID | Title | Req IDs | Dependencies | Acceptance Criteria | Test Evidence | Parallel | Complexity |
|----|-------|---------|--------------|---------------------|---------------|----------|------------|
| A-TASK-033 | Build protected panel layout | A-05 | 006,007 | Hidden when not auth; visible when auth; sections: Status, Controls, Config, Players | Browser: login shows panel | No | M |
| A-TASK-034 | Add control buttons | A-01 | 033,011,012,013 | Start (between rounds), Pause (active), Resume (paused), End (active/paused); call APIs | Browser: buttons visible per state | No | M |
| A-TASK-035 | Integrate scenario selector | A-03 | 033,021 | In Config section; label "Next Round Scenario"; disable when active | Browser: integration works | No | S |
| A-TASK-036 | Integrate duration input | A-04 | 033,024 | In Config section; label "Round Duration"; disable with message when active | Browser: integration works | No | S |
| A-TASK-037 | Integrate player table | A-02 | 033,028 | Section "Live Player Overview"; auto-updating; empty state message | Browser: table updates live | No | M |
| A-TASK-038 | Add status messages | A-01,A-05 | 034 | Success messages for actions; error messages from API; status banner; loading states | Browser: messages appear appropriately | No | S |

---

## Phase 7: Testing and Demo Readiness

| ID | Title | Req IDs | Dependencies | Acceptance Criteria | Test Evidence | Parallel | Complexity |
|----|-------|---------|--------------|---------------------|---------------|----------|------------|
| A-TASK-039 | Test admin login | A-05 | 006,007 | Correct PIN=success; incorrect=error; session persists; logout clears | Browser: dev tools cookies | No | S |
| A-TASK-040 | Test unauthenticated access | A-05 | 005 | All protected endpoints return 401; no data leak; redirect to login | curl: /api/admin/status=401 | No | S |
| A-TASK-041 | Test start round | A-01,A-03,A-04 | 014 | Start with scenario+duration; players receive event; timer starts; prices update | Integration: full flow | No | M |
| A-TASK-042 | Test pause/resume | A-01 | 019,020 | Pause: timer freeze, prices stop, trades reject; Resume: continues correctly | Manual: 10s pause test | No | M |
| A-TASK-043 | Test manual end | A-01 | 018 | Manual end=automatic end results; works when paused; P&L correct | Compare outputs | No | M |
| A-TASK-044 | Test scenarios | A-03 | 022,023 | Up trends up, Down trends down, Oscillate oscillates, Volatile=oscillate | Observe 3 rounds | No | M |
| A-TASK-045 | Test duration config | A-04 | 027 | 10s round lasts 10s; 120s lasts 2min; 5s rejected; persists per round | Timer accuracy test | No | S |
| A-TASK-046 | Test live overview | A-02 | 030,037 | Join appears in 2s; trade updates P&L; data accurate | 2-3 players trading | No | M |
| A-TASK-047 | Test no regression | A-01,A-02 | Phase 3 | Join works; trades execute; P&L updates; no console errors | Full game test | No | M |

---

## Summary

| Phase | Tasks | Complexity |
|-------|-------|------------|
| Phase 1: Auth | 7 | 3M + 4S |
| Phase 2: API | 6 | 1M + 5S |
| Phase 3: Lifecycle | 7 | 4M + 3S |
| Phase 4: Config | 7 | 7S |
| Phase 5: Overview | 5 | 1M + 4S |
| Phase 6: Frontend | 6 | 3M + 3S |
| Phase 7: Testing | 9 | 5M + 4S |
| **Total** | **47** | **18M + 30S** |

---

## Quick Reference: A-XX to Tasks

| Requirement | Tasks |
|-------------|-------|
| **A-01** Round Controls | 008, 010, 011, 012, 013, 014, 016, 017, 018, 019, 020, 034, 038, 041, 042, 043, 047 |
| **A-02** Live Player Overview | 008, 009, 028, 029, 030, 031, 032, 037, 046, 047 |
| **A-03** Scenario Selection | 010, 021, 022, 023, 035, 041, 044 |
| **A-04** Duration Adjustment | 010, 024, 025, 026, 027, 036, 041, 045 |
| **A-05** Admin Authentication | 001, 002, 003, 004, 005, 006, 007, 008, 033, 038, 039, 040 |

---

**End of Task List**
