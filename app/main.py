from datetime import datetime

from fastapi import FastAPI, Request, WebSocket, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.game_state import GameState
from app.trading_engine import TradingEngine, TradeError
from app.pnl_engine import PnLEngine
from app.ws_gateway import WebSocketManager
from app.round_manager import RoundManager
from app.auth import validate_pin, create_session, invalidate_session, require_admin, get_admin_status, ADMIN_PIN


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class NoCacheStaticFiles(StaticFiles):
    # Heuristic browser caching served stale admin/game scripts after edits.
    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-cache"
        return response


app.mount("/static", NoCacheStaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

game_state = GameState()
ws_manager = WebSocketManager()
round_manager = RoundManager(game_state, ws_manager.broadcast)
trading_engine = TradingEngine(game_state)


@app.get("/")
def join_page(request: Request):
    return templates.TemplateResponse(
        request,
        "join.html",
        {"request": request},
    )


@app.get("/intro")
def intro_page(request: Request):
    return templates.TemplateResponse(
        request,
        "intro.html",
        {"request": request},
    )


@app.get("/game")
def game_page(request: Request):
    return templates.TemplateResponse(
        request,
        "game.html",
        {"request": request},
    )


@app.get("/admin")
def admin_page(request: Request):
    return templates.TemplateResponse(
        request,
        "admin.html",
        {"request": request},
    )


@app.get("/admin/game-status")
def get_game_status():
    """Get current game status for admin UI."""
    round_state = game_state.round_state
    return {
        "current_round": round_state.round_number if round_state.round_number > 0 else None,
        "next_round_number": game_state.next_round_number,
        "total_rounds": game_state.total_rounds,
        "round_active": round_state.is_active,
        "game_started": game_state.next_round_number > 1 or round_state.is_active,
        "game_complete": game_state.next_round_number > game_state.total_rounds and not round_state.is_active,
        "round_duration_seconds": game_state.round_duration_seconds,
        "scenario_schedule": game_state.scenario_schedule,
        "admin_overrides": game_state.admin_overrides,
    }


@app.get("/admin/scenario-schedule")
def get_scenario_schedule():
    """Get the scenario schedule for all rounds."""
    return {
        "total_rounds": game_state.total_rounds,
        "scenario_schedule": game_state.scenario_schedule,
        "admin_overrides": game_state.admin_overrides,
    }


@app.post("/admin/scenario-schedule")
async def set_scenario_schedule(request: Request):
    """Set or update the scenario schedule. Generates random if empty."""
    data = await request.json()
    total_rounds = data.get("total_rounds", game_state.total_rounds)
    overrides = data.get("overrides", {})

    # Validate total_rounds
    if not isinstance(total_rounds, int) or total_rounds < 1:
        raise HTTPException(status_code=400, detail="total_rounds must be an integer >= 1")

    game_state.total_rounds = total_rounds

    # Generate new random schedule if none exists or total_rounds changed
    if not game_state.scenario_schedule or len(game_state.scenario_schedule) != total_rounds:
        game_state.scenario_schedule = round_manager.generate_scenario_schedule(total_rounds)

    # Apply admin overrides
    valid_scenarios = {"up", "down", "oscillate"}
    for round_num, scenario in overrides.items():
        round_int = int(round_num)
        if 1 <= round_int <= total_rounds and scenario in valid_scenarios:
            game_state.admin_overrides[round_int] = scenario

    return {
        "total_rounds": game_state.total_rounds,
        "scenario_schedule": game_state.scenario_schedule,
        "admin_overrides": game_state.admin_overrides,
    }


@app.post("/join")
async def join(request: Request):
    data = await request.json()
    name = data.get("name", "").strip()

    if not name:
        raise HTTPException(status_code=400, detail="Name is required")

    player = game_state.add_player(name)

    return {
        "player_id": player.player_id,
        "role": player.role,
        "session_token": player.session_token,
        "start_position": player.start_position,
        "current_position": player.current_position,
    }


@app.get("/briefing-status")
def briefing_status(session_token: str = ""):
    """Briefing state for a player: whether they ticked the checkbox and whether the admin released the lobby."""
    player = game_state.get_player_by_token(session_token)
    if player is None:
        raise HTTPException(status_code=404, detail="Player session not found")
    return {
        "ready": player.briefing_ready,
        "briefing_released": game_state.briefing_released,
        "role": player.role,
    }


@app.post("/briefing/ready")
async def briefing_ready(request: Request):
    data = await request.json()
    player = game_state.get_player_by_token(data.get("session_token", ""))
    if player is None:
        raise HTTPException(status_code=404, detail="Player session not found")

    player.briefing_ready = bool(data.get("ready", True))
    return {"ready": player.briefing_ready, "briefing_released": game_state.briefing_released}


@app.post("/admin/start-round")
async def start_round(request: Request):
    data = await request.json()
    scenario = data.get("scenario")
    scenario2 = data.get("scenario2")
    total_rounds = data.get("total_rounds")
    duration_seconds = data.get("duration_seconds")

    if scenario not in {"up", "down", "oscillate"}:
        raise HTTPException(
            status_code=400,
            detail="Scenario must be up, down, or oscillate",
        )

    if game_state.round_state.is_active:
        raise HTTPException(
            status_code=400,
            detail="A round is already active",
        )

    if not game_state.briefing_released:
        raise HTTPException(status_code=400, detail="The briefing has not been released yet")

    try:
        await round_manager.start_round(
            scenario=scenario,
            scenario2=scenario2,
            duration_seconds=duration_seconds,
            total_rounds=total_rounds
        )
        return {
            "status": "started",
            "scenario": scenario,
            "total_rounds": game_state.total_rounds,
            "duration_seconds": game_state.round_duration_seconds,
        }

    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/admin/restart")
async def restart_game():
    """
    Restart the game completely.
    Resets all game state, removes all players, stops active rounds.
    Broadcasts game_restarted event to all connected clients.
    """
    # Cancel any active round without finalizing P&L
    round_manager.cancel_active_round()

    # Reset the game state
    game_state.reset()

    # Broadcast game restarted event to all clients
    await ws_manager.broadcast(
        "game_restarted",
        {
            "message": "Game restarted by admin. Please join again.",
            "game_generation": game_state.game_generation,
        },
    )

    return {"status": "restarted"}


def _build_trade_payload(player, direction: str, round_state) -> dict:
    """Build the trade_executed payload with mark-to-market fields."""
    break_even = PnLEngine.compute_break_even(player)
    status = PnLEngine.compute_status_indicator(player, round_state.current_mid_price)

    # Get the last trade for P&L contribution and auto-closeout flag
    last_trade = player.trade_history[-1] if player.trade_history else None
    trade_pnl = last_trade.pnl_contribution if last_trade else 0.0
    is_auto_closeout = last_trade.is_auto_closeout if last_trade else False

    payload = {
        "player_id": player.player_id,
        "name": player.name,
        "role": player.role,
        "direction": direction,
        "price": round_state.last_traded_price,
        "new_position": player.current_position,
        "current_cash": round(player.current_cash, 2),
        "expected_cash": round(player.expected_cash, 2),
        "round_pnl": player.round_pnl,
        "cumulative_pnl": player.cumulative_pnl,
        "break_even_price": break_even,
        "status_indicator": status,
        "last_traded_price": round_state.last_traded_price,
        "trade_pnl_contribution": round(trade_pnl, 2),
        "is_auto_closeout": is_auto_closeout,
    }

    # Role-specific fields
    if player.role == "Generator" and player.cost_basis is not None:
        payload["cost_basis"] = player.cost_basis
    elif player.role == "Retailer" and player.tariff is not None:
        payload["tariff"] = player.tariff

    return payload


# =============================================================================
# Admin API Endpoints (Module A)
# =============================================================================

@app.post("/api/admin/login")
async def admin_login(request: Request):
    """Authenticate admin with PIN and create session."""
    data = await request.json()
    pin = data.get("pin", "")

    if not validate_pin(pin):
        return JSONResponse(
            status_code=401,
            content={"error": "Invalid PIN"}
        )

    token, expires_at = create_session()

    response = JSONResponse(
        content={
            "authenticated": True,
            "token": token,
            "expires_at": expires_at.isoformat()
        }
    )

    # Set HTTP-only cookie with session token
    response.set_cookie(
        key="admin_session",
        value=token,
        httponly=True,
        secure=False,  # Set to True in production with HTTPS
        samesite="lax",
        max_age=8 * 60 * 60  # 8 hours
    )

    return response


@app.post("/api/admin/logout")
async def admin_logout(request: Request, admin_token: str = Depends(require_admin)):
    """Invalidate admin session."""
    invalidate_session(admin_token)

    response = JSONResponse(content={"status": "logged_out"})
    response.delete_cookie(key="admin_session")

    return response


@app.get("/api/admin/status")
async def admin_status(request: Request, admin_token: str = Depends(require_admin)):
    """Get admin-visible game state."""
    round_state = game_state.round_state

    # Calculate remaining seconds
    if round_state.is_paused:
        remaining = round_state.paused_remaining_seconds
    elif round_state.ends_at:
        remaining = int((round_state.ends_at - datetime.utcnow()).total_seconds())
        remaining = max(0, remaining)
    else:
        remaining = max(0, round_state.duration_seconds - round_state.elapsed_seconds)

    return {
        "authenticated": True,
        "round_active": round_state.is_active,
        "round_paused": round_state.is_paused,
        "current_round": round_state.round_number if round_state.round_number > 0 else None,
        "next_round_number": game_state.next_round_number,
        "total_rounds": game_state.total_rounds,
        "scenario": round_state.scenario,
        "scenario2": round_state.scenario2,
        "duration_seconds": round_state.duration_seconds,
        "remaining_seconds": remaining,
        "price_mode": game_state.price_mode,
        "game_complete": game_state.next_round_number > game_state.total_rounds and not round_state.is_active,
        "briefing_released": game_state.briefing_released,
        "players_ready": sum(1 for p in game_state.players.values() if p.briefing_ready),
        "players_total": len(game_state.players),
    }


@app.get("/api/admin/players")
async def admin_players(request: Request, admin_token: str = Depends(require_admin)):
    """Get live player overview for admin panel."""
    players_data = []

    for player in game_state.players.values():
        # Count trades in current round
        trade_count = len([t for t in player.trade_history if t.round_number == game_state.round_state.round_number])

        players_data.append({
            "player_id": player.player_id,
            "name": player.name,
            "role": player.role,
            "position": player.current_position,
            "round_pnl": round(player.round_pnl, 2),
            "cumulative_pnl": round(player.cumulative_pnl, 2),
            "connected": player.connected,
            "trade_count": trade_count,
            "briefing_ready": player.briefing_ready,
        })

    return {
        "players": players_data,
        "count": len(players_data)
    }


@app.post("/api/admin/release-briefing")
async def api_release_briefing(request: Request, admin_token: str = Depends(require_admin)):
    """Move all players from the briefing page to the game lobby once everyone has confirmed reading it."""
    if not game_state.players:
        raise HTTPException(status_code=400, detail="No players have joined yet")

    waiting = [p.name for p in game_state.players.values() if not p.briefing_ready]
    if waiting:
        raise HTTPException(
            status_code=400,
            detail=f"Not everyone has confirmed yet: {', '.join(waiting)}",
        )

    game_state.briefing_released = True
    await ws_manager.broadcast("briefing_released", {})
    return {"status": "released"}


@app.post("/api/admin/start-round")
async def api_start_round(request: Request, admin_token: str = Depends(require_admin)):
    """Start the next round with selected scenario and duration."""
    data = await request.json()

    scenario = data.get("scenario")
    scenario2 = data.get("scenario2")
    duration_seconds = data.get("duration_seconds")
    total_rounds = data.get("total_rounds")
    price_mode = data.get("price_mode")

    # Normalize scenario (volatile -> oscillate)
    if scenario == "volatile":
        scenario = "oscillate"
    elif scenario not in {"up", "down", "oscillate"}:
        raise HTTPException(
            status_code=400,
            detail="Scenario must be up, down, or oscillate"
        )

    if scenario2 == "volatile":
        scenario2 = "oscillate"
    elif scenario2 is not None and scenario2 not in {"up", "down", "oscillate"}:
        raise HTTPException(
            status_code=400,
            detail="Second scenario must be up, down, or oscillate",
        )

    # Validate duration
    if duration_seconds is not None:
        if not isinstance(duration_seconds, int) or duration_seconds < 10:
            raise HTTPException(
                status_code=400,
                detail="Duration must be at least 10 seconds"
            )

    # Validate total_rounds
    if total_rounds is not None:
        if not isinstance(total_rounds, int) or total_rounds < 1:
            raise HTTPException(
                status_code=400,
                detail="Total rounds must be at least 1"
            )

    if price_mode is not None and price_mode not in {"hard", "easy"}:
        raise HTTPException(status_code=400, detail="Price mode must be hard or easy")

    # Check if round already active
    if game_state.round_state.is_active:
        raise HTTPException(
            status_code=400,
            detail="A round is already active"
        )

    if not game_state.briefing_released:
        raise HTTPException(
            status_code=400,
            detail="Release the briefing before starting the game"
        )

    try:
        await round_manager.start_round(
            scenario=scenario,
            scenario2=scenario2,
            duration_seconds=duration_seconds,
            total_rounds=total_rounds,
            price_mode=price_mode,
        )

        return {
            "status": "started",
            "round_number": game_state.round_state.round_number,
            "scenario": scenario,
            "scenario2": game_state.round_state.scenario2,
            "duration_seconds": game_state.round_duration_seconds,
            "price_mode": game_state.price_mode,
        }

    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/admin/pause-round")
async def api_pause_round(request: Request, admin_token: str = Depends(require_admin)):
    """Pause the active round."""
    try:
        result = await round_manager.pause_round()
        return result
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/admin/resume-round")
async def api_resume_round(request: Request, admin_token: str = Depends(require_admin)):
    """Resume a paused round."""
    try:
        result = await round_manager.resume_round()
        return result
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/admin/end-round")
async def api_end_round(request: Request, admin_token: str = Depends(require_admin)):
    """Manually end the current round."""
    try:
        result = await round_manager.end_round_manual()
        return result
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# =============================================================================
# Player Trading Endpoint
# =============================================================================

@app.post("/trade")
async def trade(request: Request):
    data = await request.json()

    token = data.get("session_token")
    direction = data.get("direction")

    if direction not in {"buy", "sell"}:
        raise HTTPException(
            status_code=400,
            detail="Trade direction must be buy or sell",
        )

    # Check if round is active and not paused
    round_state = game_state.round_state
    if not round_state.is_active:
        raise HTTPException(
            status_code=400,
            detail="No active round. Trading is not allowed.",
        )
    if round_state.is_paused:
        raise HTTPException(
            status_code=400,
            detail="Trading is paused",
        )

    try:
        player = trading_engine.execute_trade(token, direction)

    except TradeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    round_state = game_state.round_state
    trade_payload = _build_trade_payload(player, direction, round_state)

    await ws_manager.broadcast("trade_executed", trade_payload)

    remaining_seconds = (
        max(0, int((round_state.ends_at - datetime.utcnow()).total_seconds()))
        if round_state.ends_at
        else round_state.duration_seconds
    )

    await ws_manager.broadcast(
        "price_update",
        {
            "bid": round_state.bid_price,
            "offer": round_state.offer_price,
            "last_traded_price": round_state.last_traded_price,
            "price_history": [
                {
                    "timestamp": p.timestamp.isoformat(),
                    "mid": p.mid,
                    "bid": p.bid,
                    "offer": p.offer,
                }
                for p in round_state.price_history[-60:]
            ],
            "remaining_seconds": remaining_seconds,
        },
    )

    return {"status": "ok", **trade_payload}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)

    try:
        if game_state.round_state.is_active:
            round_state = game_state.round_state

            remaining_seconds = (
                max(0, int((round_state.ends_at - datetime.utcnow()).total_seconds()))
                if round_state.ends_at
                else round_state.duration_seconds
            )
            progress = (
                round_state.elapsed_seconds / round_state.duration_seconds
                if round_state.duration_seconds
                else 0.0
            )
            signal_payload = round_manager.get_market_signal_payload(progress)

            await ws_manager.send_json(
                websocket,
                {
                    "type": "round_started",
                    "payload": {
                        "round_number": round_state.round_number,
                        "scenario": round_state.scenario,
                        "scenario2": round_state.scenario2,
                        "active_scenario": signal_payload["active_scenario"],
                        "phase_number": signal_payload["phase_number"],
                        "news": round_state.news_event,
                        "market_signals": signal_payload["market_signals"],
                        "start_price": round_state.start_price,
                        "duration_seconds": round_state.duration_seconds,
                        "remaining_seconds": remaining_seconds,
                    },
                },
            )

            await ws_manager.send_json(
                websocket,
                {
                    "type": "price_update",
                    "payload": {
                        "bid": round_state.bid_price,
                        "offer": round_state.offer_price,
                        "last_traded_price": round_state.last_traded_price,
                        "price_history": [
                            {
                                "timestamp": p.timestamp.isoformat(),
                                "mid": p.mid,
                                "bid": p.bid,
                                "offer": p.offer,
                            }
                            for p in round_state.price_history[-60:]
                        ],
                        "remaining_seconds": remaining_seconds,
                    },
                },
            )

        while True:
            await websocket.receive_text()

    except Exception:
        pass

    finally:
        await ws_manager.disconnect(websocket)