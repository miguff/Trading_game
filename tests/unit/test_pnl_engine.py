import asyncio

import pytest

from app.game_state import GameState
from app.pnl_engine import PnLEngine
from app.round_manager import RoundManager

async def _dummy_broadcaster(event_type: str, payload: dict) -> None:
    return None


def _prepare_round(game_state, start_price=50.0):
    """Helper to prepare a new round with all required args."""
    game_state.prepare_new_round(
        start_price=start_price,
        target_end_price=start_price,
        scenario="up",
        news_event="Test news",
        duration_seconds=90,
    )


def test_generator_initial_pnl():
    """Generator at round start: cost_basis=47.50, expected_cash=-475, position=+10, mid=50."""
    game_state = GameState()
    generator = game_state.add_player("Generator")  # 1st player -> Generator
    assert generator.role == "Generator"

    _prepare_round(game_state, 50.0)

    # Verify role economics
    assert generator.cost_basis == 47.50
    assert generator.expected_cash == -475.0
    assert generator.current_position == 10
    assert generator.current_cash == 0.0

    # Live P&L = current_cash + expected_cash + (mid_price × current_position)
    # = 0 + (-475) + (50 × 10) = -475 + 500 = 25
    generator_pnl = PnLEngine.compute_current_round_pnl(generator, game_state.round_state)
    assert generator_pnl == 25.0

    # Break-even = -(0 + (-475)) / 10 = 475 / 10 = 47.50
    be = PnLEngine.compute_break_even(generator)
    assert be == 47.50

    # Status: mid (50) >= break-even (47.50) => "In profit zone"
    status = PnLEngine.compute_status_indicator(generator, game_state.round_state.current_mid_price)
    assert status == "In profit zone"


def test_retailer_initial_pnl():
    """Retailer at round start: tariff=52.50, expected_cash=+525, position=-10, mid=50."""
    game_state = GameState()
    game_state.add_player("Alice")  # 1st -> Generator
    retailer = game_state.add_player("Retailer")  # 2nd -> Retailer
    assert retailer.role == "Retailer"

    _prepare_round(game_state, 50.0)

    # Verify role economics
    assert retailer.tariff == 52.50
    assert retailer.expected_cash == 525.0
    assert retailer.current_position == -10
    assert retailer.current_cash == 0.0

    # Live P&L = 0 + 525 + (50 × -10) = 525 - 500 = 25
    retailer_pnl = PnLEngine.compute_current_round_pnl(retailer, game_state.round_state)
    assert retailer_pnl == 25.0

    # Break-even = -(0 + 525) / (-10) = -525 / -10 = 52.50
    be = PnLEngine.compute_break_even(retailer)
    assert be == 52.50

    # Status: mid (50) <= break-even (52.50) => "In profit zone"
    status = PnLEngine.compute_status_indicator(retailer, game_state.round_state.current_mid_price)
    assert status == "In profit zone"


def test_trader_initial_pnl():
    """Trader at round start: expected_cash=0, position=0, mid=50."""
    game_state = GameState()
    game_state.add_player("Alice")  # 1st -> Generator
    game_state.add_player("Bob")  # 2nd -> Retailer
    trader = game_state.add_player("Carol")  # 3rd -> Trader
    assert trader.role == "Trader"

    _prepare_round(game_state, 50.0)

    assert trader.expected_cash == 0.0
    assert trader.current_position == 0
    assert trader.current_cash == 0.0

    # Live P&L = 0 + 0 + (50 × 0) = 0
    current_pnl = PnLEngine.compute_current_round_pnl(trader, game_state.round_state)
    assert current_pnl == 0.0

    # Break-even is None when position is 0
    be = PnLEngine.compute_break_even(trader)
    assert be is None

    status = PnLEngine.compute_status_indicator(trader, game_state.round_state.current_mid_price)
    assert status == "Position flat — P&L locked"


def test_generator_after_sell():
    """Generator sells 5 MWh at bid 55, mid=55."""
    game_state = GameState()
    generator = game_state.add_player("Generator")
    _prepare_round(game_state, 50.0)

    # Sell 5 MWh at bid 55
    generator.current_position = 5
    generator.current_cash = 5 * 55  # +275
    game_state.round_state.current_mid_price = 55.0

    # P&L = 275 + (-475) + (55 × 5) = 275 - 475 + 275 = 75
    pnl = PnLEngine.compute_current_round_pnl(generator, game_state.round_state)
    assert pnl == 75.0

    # Break-even = -(275 + (-475)) / 5 = 200 / 5 = 40.00
    be = PnLEngine.compute_break_even(generator)
    assert be == 40.00

    # Status: mid (55) >= break-even (40) => "In profit zone"
    status = PnLEngine.compute_status_indicator(generator, game_state.round_state.current_mid_price)
    assert status == "In profit zone"


def test_trader_buy_and_pnl():
    """Trader buys 1 MWh at offer 51, mid=50."""
    game_state = GameState()
    game_state.add_player("Alice")
    game_state.add_player("Bob")
    trader = game_state.add_player("Carol")
    _prepare_round(game_state, 50.0)

    trader.current_position = 1
    trader.current_cash = -51.0
    game_state.round_state.current_mid_price = 50.0

    # P&L = -51 + 0 + (50 × 1) = -51 + 50 = -1
    pnl = PnLEngine.compute_current_round_pnl(trader, game_state.round_state)
    assert pnl == -1.0

    # Break-even = -(-51 + 0) / 1 = 51.0
    be = PnLEngine.compute_break_even(trader)
    assert be == 51.0

    # Status: position > 0, mid (50) < break-even (51) => "Need price ≥ 51.00"
    status = PnLEngine.compute_status_indicator(trader, game_state.round_state.current_mid_price)
    assert status == "Need price ≥ 51.00"


def test_round_manager_enforces_total_rounds():
    game_state = GameState()
    round_manager = RoundManager(game_state, _dummy_broadcaster)
    game_state.next_round_number = game_state.total_rounds + 1

    with pytest.raises(RuntimeError, match="Game over"):
        asyncio.run(round_manager.start_round("up", duration_seconds=1))


def test_generator_position_carries_and_receives_new_round_allocation():
    game_state = GameState()
    generator = game_state.add_player("Generator")
    _prepare_round(game_state, 50.0)
    generator.current_position = 7
    generator.current_cash = 150.0
    game_state.round_state.current_mid_price = 55.0
    PnLEngine.finalize_round(generator, game_state.round_state)

    assert generator.current_position == 7

    game_state.next_round_number = 2
    game_state.prepare_new_round(
        start_price=55.0,
        target_end_price=50.0,
        scenario="down",
        news_event="Second round",
        duration_seconds=90,
        is_final_round=True,
    )

    assert generator.round_opening_position == 7
    assert generator.current_position == 17
    assert generator.max_position == 27
    assert PnLEngine.compute_current_round_pnl(generator, game_state.round_state) == 27.5

    game_state.round_state.current_mid_price = 50.0
    PnLEngine.finalize_round(generator, game_state.round_state)

    assert generator.current_position == 17
    assert generator.round_pnl == -57.5
    assert generator.cumulative_pnl == 2.5


def test_round_started_broadcast_includes_carried_position():
    game_state = GameState()
    generator = game_state.add_player("Generator")
    _prepare_round(game_state, 50.0)
    generator.current_position = 7
    game_state.next_round_number = 2
    game_state.prepare_new_round(
        start_price=55.0,
        target_end_price=60.0,
        scenario="up",
        news_event="Second round",
        duration_seconds=90,
    )
    broadcast = {}

    async def capture_broadcast(event_type, payload):
        broadcast["event_type"] = event_type
        broadcast["payload"] = payload

    round_manager = RoundManager(game_state, capture_broadcast)
    asyncio.run(round_manager._broadcast_round_started())

    player_state = broadcast["payload"]["player_state"][generator.player_id]
    assert broadcast["event_type"] == "round_started"
    assert player_state["position"] == 17
    assert player_state["round_pnl"] == 27.5


def test_round_end_trade_history_includes_trade_pnl_contribution():
    game_state = GameState()
    player = game_state.add_player("Alice")
    _prepare_round(game_state)
    player.record_trade(
        direction="sell",
        price=49.0,
        quantity=1,
        round_number=game_state.round_state.round_number,
        pnl_contribution=1.5,
        resulting_position=9,
    )
    broadcast = {}

    async def capture_broadcast(event_type, payload):
        broadcast["event_type"] = event_type
        broadcast["payload"] = payload

    round_manager = RoundManager(game_state, capture_broadcast)
    asyncio.run(round_manager._broadcast_round_ended(close_price=50.0))

    trade = broadcast["payload"]["player_summary"][0]["trade_history"][0]
    assert broadcast["event_type"] == "round_ended"
    assert trade["pnl_contribution"] == 1.5
