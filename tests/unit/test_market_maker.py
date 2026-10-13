from app.market_maker import MarketMaker


def test_final_round_does_not_force_price_back_to_game_start(monkeypatch):
    import app.market_maker as market_maker_module

    monkeypatch.setattr(market_maker_module.random, "gauss", lambda mean, sigma: 0.0)
    monkeypatch.setattr(market_maker_module.random, "random", lambda: 1.0)
    market_maker = MarketMaker()

    price = market_maker.calculate_next_mid_price(
        previous_mid=55.0,
        game_start_price=50.0,
        round_start_price=55.0,
        target_end_price=50.0,
        scenario="up",
        progress=1.0,
        is_final_round=True,
    )

    assert price > 50.0


def test_up_and_down_scenarios_apply_opposite_directional_drift(monkeypatch):
    import app.market_maker as market_maker_module

    monkeypatch.setattr(market_maker_module.random, "gauss", lambda mean, sigma: 0.0)
    monkeypatch.setattr(market_maker_module.random, "random", lambda: 1.0)

    def next_price(scenario):
        return MarketMaker().calculate_next_mid_price(
            previous_mid=50.0,
            game_start_price=50.0,
            round_start_price=50.0,
            target_end_price=50.0,
            scenario=scenario,
            progress=0.5,
            is_final_round=False,
        )

    assert next_price("up") > 50.0
    assert next_price("down") < 50.0


def test_finalize_round_preserves_closing_position_and_cash():
    from app.game_state import GameState
    from app.pnl_engine import PnLEngine

    game_state = GameState()
    player = game_state.add_player("Trader")
    game_state.prepare_new_round(
        start_price=50.0,
        target_end_price=55.0,
        scenario="up",
        news_event="test",
        duration_seconds=10,
    )
    player.current_position = 3
    player.current_cash = -153.0
    game_state.round_state.current_mid_price = 55.0

    PnLEngine.finalize_round(player, game_state.round_state)

    assert player.current_position == 3
    assert player.current_cash == -153.0