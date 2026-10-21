import asyncio
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import app.main as main


@pytest.mark.parametrize("source", ["tick", "trade", "reconnect"])
def test_price_updates_keep_ten_minutes_of_history(monkeypatch, source):
    history = [
        SimpleNamespace(timestamp=datetime(2026, 1, 1), mid=index, bid=index - 1, offer=index + 1)
        for index in range(650)
    ]
    round_state = SimpleNamespace(
        is_active=True,
        is_paused=False,
        ends_at=None,
        duration_seconds=90,
        elapsed_seconds=1,
        round_number=1,
        scenario="up",
        scenario2="up",
        news_event="",
        start_price=50,
        bid_price=49,
        offer_price=51,
        last_traded_price=50,
        price_history=history,
    )
    state = SimpleNamespace(round_state=round_state)
    messages = []

    async def broadcast(event_type, payload):
        messages.append({"type": event_type, "payload": payload})

    async def send_json(websocket, message):
        messages.append(message)

    manager = SimpleNamespace(
        connect=AsyncMock(),
        disconnect=AsyncMock(),
        broadcast=broadcast,
        send_json=send_json,
    )
    round_manager = main.RoundManager(state, broadcast)
    monkeypatch.setattr(main, "game_state", state)
    monkeypatch.setattr(main, "ws_manager", manager)
    monkeypatch.setattr(main, "round_manager", round_manager)
    monkeypatch.setattr(round_manager, "get_market_signal_payload", lambda progress: {
        "active_scenario": "up", "phase_number": 1, "market_signals": {},
    })

    if source == "tick":
        asyncio.run(round_manager._broadcast_price_update())
    elif source == "trade":
        monkeypatch.setattr(main.trading_engine, "execute_trade", lambda token, direction: object())
        monkeypatch.setattr(main, "_build_trade_payload", lambda *args: {})
        request = SimpleNamespace(json=AsyncMock(return_value={
            "session_token": "test-player", "direction": "buy",
        }))
        asyncio.run(main.trade(request))
    else:
        websocket = SimpleNamespace(receive_text=AsyncMock(side_effect=RuntimeError("closed")))
        asyncio.run(main.websocket_endpoint(websocket))

    prices = [message["payload"] for message in messages if message["type"] == "price_update"]
    assert len(prices) == 1
    assert len(prices[0]["price_history"]) == 600
    assert prices[0]["price_history"][0]["mid"] == 50
    assert prices[0]["price_history"][-1]["mid"] == 649