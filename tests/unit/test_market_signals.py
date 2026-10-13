from app.market_signals import DOWN_SIGNALS, UP_SIGNALS, get_market_signal, market_signal_to_dict


def test_workbook_headlines_replace_generic_scenario_news():
    assert len(UP_SIGNALS) == 14
    assert len(DOWN_SIGNALS) == 7
    assert get_market_signal("up", seed=1).headline == (
        "Colder Weather and Supply Concerns Lift TTF Day-Ahead 5%"
    )
    assert get_market_signal("down", seed=1).headline == (
        "Iran Talks and Warmer Weather Push TTF Day-Ahead Lower"
    )


def test_each_round_has_one_news_item_and_three_rotating_weather_items():
    first_round = get_market_signal("up", seed=1)
    second_round = get_market_signal("up", seed=2)

    assert len(first_round.cards) == 3
    assert len(second_round.cards) == 3
    assert first_round.headline != second_round.headline
    assert first_round.cards[0].title != second_round.cards[0].title


def test_rotating_weather_items_use_workbook_facts_and_units():
    storage = get_market_signal("up", seed=1).cards[0]
    july_storage = get_market_signal("up", seed=2).cards[0]
    wind = get_market_signal("up", seed=2).cards[2]
    solar = get_market_signal("up", seed=3).cards[2]

    assert storage.title == "European Gas Storage"
    assert storage.value_label == "28% in April"
    assert "50 bcm (46% full)" in storage.summary
    assert july_storage.title == "July Storage Update"
    assert wind.value_label == "4.7 GW forecast"
    assert solar.value_label == "22.57%; 48 TWh"


def test_serialized_weather_metrics_do_not_claim_probability():
    signal_data = market_signal_to_dict(get_market_signal("down", seed=1))
    assert len(signal_data["cards"]) == 3
    storage_card = next(
        card for card in signal_data["cards"] if card["title"] == "European Gas Storage"
    )

    assert storage_card["value_label"] == "28% in April"
    assert storage_card["probability"] is None