import pytest

from app.market_signals import NEWS_POOL, get_market_signal, market_signal_to_dict

SCENARIOS = ("up", "down", "oscillate")


def test_pool_has_every_mode_kind_and_scenario():
    assert set(NEWS_POOL) == {"easy", "hard"}
    for mode in NEWS_POOL.values():
        assert set(mode) == {"news", "weather"}
        for kind in mode.values():
            assert set(kind) == set(SCENARIOS)
            assert all(len(items) > 0 for items in kind.values())


@pytest.mark.parametrize("mode", ["easy", "hard"])
@pytest.mark.parametrize("scenario", SCENARIOS)
def test_signal_uses_matching_pool_entries(mode, scenario):
    signal = get_market_signal(scenario, seed=1, mode=mode)

    assert signal.headline == NEWS_POOL[mode]["news"][scenario][0]
    assert len(signal.cards) == 3
    assert signal.body.endswith(NEWS_POOL[mode]["weather"][scenario][0])


def test_seed_rotates_and_wraps_through_the_column():
    items = NEWS_POOL["hard"]["news"]["down"]

    assert get_market_signal("down", seed=2, mode="hard").headline == items[1]
    assert get_market_signal("down", seed=len(items) + 1, mode="hard").headline == items[0]


def test_easy_mode_is_hungarian_and_hard_mode_is_english():
    assert get_market_signal("up", seed=1, mode="easy").body.startswith("Időjárás: ")
    assert get_market_signal("up", seed=1, mode="easy").cards[0].title == "Hőmérséklet"
    assert get_market_signal("up", seed=1, mode="hard").body.startswith("Weather: ")
    assert get_market_signal("up", seed=1, mode="hard").cards[0].title == "Temperature"


def test_shock_signals_are_unchanged_by_mode():
    assert get_market_signal("surge", seed=1, mode="easy").scenario == "surge"
    assert get_market_signal("crash", seed=1, mode="hard").cards == []


def test_weather_charts_follow_scenario_direction():
    up = get_market_signal("up", seed=1, mode="hard").cards
    down = get_market_signal("down", seed=1, mode="easy").cards

    temperature, wind, demand = up
    assert temperature.values[-1] < temperature.values[0]
    assert wind.values[-1] < wind.values[0]
    assert demand.values[-1] > demand.values[0]
    assert [c.chart_type for c in up] == ["line", "bar", "area"]
    assert down[2].values[-1] < down[2].values[0]
    assert all(c.value_label == "" for c in up + down)


def test_serialized_signal_includes_chart_data():
    cards = market_signal_to_dict(get_market_signal("oscillate", seed=1, mode="hard"))["cards"]

    assert len(cards) == 3
    assert all(len(card["values"]) > 2 and card["probability"] is None for card in cards)
