"""Workbook-backed news and weather signals for the energy trading game."""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import random


@dataclass
class ForecastCard:
    """A weather or market metric with compact chart data."""
    type: str
    title: str
    summary: str
    values: List[float]
    chart_type: str
    color: str
    value_label: str
    probability: Optional[int] = None


@dataclass
class MarketSignal:
    """A round bulletin paired with the workbook's weather context."""
    headline: str
    body: str
    scenario: str
    cards: List[ForecastCard]


def _weather_cards() -> List[ForecastCard]:
    return [
        ForecastCard(
            type="demand",
            title="European Gas Storage",
            summary=(
                "Inventories entered April at 28%, versus 35% a year earlier. "
                "On 23 June, storage was 50 bcm (46% full), 10.6 bcm below 2025 "
                "and 15 bcm below the five-year average."
            ),
            values=[35, 28],
            chart_type="bar",
            color="#f87171",
            value_label="28% in April",
        ),
        ForecastCard(
            type="demand",
            title="July Storage Update",
            summary=(
                "EU storage was 51.5% full on 10 July, up from 49.7% the prior "
                "weekend, but 17 percentage points below last year and 22.9 points "
                "below the five-year average."
            ),
            values=[49.7, 51.5],
            chart_type="line",
            color="#fbbf24",
            value_label="51.5% on 10 July",
        ),
        ForecastCard(
            type="outage",
            title="Heatwave and French Nuclear",
            summary=(
                "River temperatures are expected to stay high through much of summer. "
                "Above 40 C, output was cut by over 9 GW for several days across 12 "
                "of 57 reactors; two more were expected offline, four limited, and "
                "another offline due to low river levels."
            ),
            values=[0, 9],
            chart_type="bar",
            color="#ef4444",
            value_label="Over 9 GW curtailed",
        ),
        ForecastCard(
            type="wind",
            title="German Wind Forecast",
            summary=(
                "German wind output was expected to fall by 8.1 GW to 4.7 GW, "
                "around 60% below the seasonal average."
            ),
            values=[8.1, 4.7],
            chart_type="line",
            color="#60a5fa",
            value_label="4.7 GW forecast",
        ),
        ForecastCard(
            type="solar",
            title="EU Solar Generation",
            summary=(
                "In May, solar became the EU27's largest electricity source at "
                "22.57% of generation, setting a monthly record of 48 TWh."
            ),
            values=[22.57],
            chart_type="bar",
            color="#fbbf24",
            value_label="22.57%; 48 TWh",
        ),
        ForecastCard(
            type="demand",
            title="Heatwave Power Demand",
            summary=(
                "Late-June and mid-July heat drove cooling demand. Reduced French "
                "nuclear output, lower German and British gas-plant output, and "
                "low wind speeds added to price pressure."
            ),
            values=[1, 2, 3],
            chart_type="area",
            color="#f87171",
            value_label="Cooling demand rising",
        ),
    ]


WEATHER_CARDS = _weather_cards()


def _signals(scenario: str, items: List[tuple]) -> List[MarketSignal]:
    signals = []
    for headline, body, price_move in items:
        if price_move:
            body = f"{body} Spreadsheet price move: {price_move}."
        signals.append(
            MarketSignal(
                headline=headline,
                body=body,
                scenario=scenario,
                cards=[],
            )
        )
    return signals


UP_SIGNALS = _signals("up", [
    (
        "Colder Weather and Supply Concerns Lift TTF Day-Ahead 5%",
        "Colder forecasts, concerns about French nuclear availability, low storage, "
        "bullish carbon prices, and rising geopolitical tensions supported TTF.",
        "30 to 38",
    ),
    (
        "Short Covering and Colder Temperatures Push TTF Up 14%",
        "Increased short covering after last week's gains, colder temperatures, and "
        "storage concerns drove another sharp rise.",
        "35 to 40",
    ),
    (
        "Rising Iran Tensions Put TTF Day-Ahead Up 12%",
        "Rising geopolitical tensions and the prospect of a US attack on Iran lifted "
        "prices.",
        "30 to 33",
    ),
    (
        "Strait of Hormuz Disruption Sends Spot Gas Up 33%",
        "US and Israeli attacks on Iran were followed by suspended vessel traffic "
        "around the Strait of Hormuz and QatarEnergy's force majeure declaration.",
        "33 to 45",
    ),
    (
        "LNG Supply Concerns Drive Another 23% TTF Gain",
        "TTF day-ahead surged again as the conflict showed no signs of easing. LNG "
        "supply concerns remained a key risk for European gas markets.",
        "45 to 53",
    ),
    (
        "Attack on South Pars Field Renews Market Fears",
        "Markets rallied after a US attack on the South Pars gas field. Iran vowed "
        "to target energy assets in the region.",
        "45 to 50",
    ),
    (
        "Ras Laffan Damage Threatens Long-Term LNG Supply",
        "Iran retaliated by striking Ras Laffan twice. QatarEnergy reported extensive "
        "damage, with 17% (12.8 Mt) of production affected for the next three to five years.",
        "50 to 60",
    ),
    (
        "Ceasefire Uncertainty and US Port Blockade Lift Prices 5%",
        "Fresh uncertainty around a ceasefire and a US blockade of Iranian ports added "
        "risk premium to gas prices.",
        "43 to 48",
    ),
    (
        "QatarEnergy Extends LNG Force Majeure",
        "LNG supply concerns resurfaced after QatarEnergy extended force majeure for "
        "shipments to Italy and one Asian buyer.",
        "41 to 44",
    ),
    (
        "Attacks on Ships Break Ceasefire and Raise LNG Risk",
        "The US and Iran traded attacks after Iran struck three ships in the Strait of "
        "Hormuz, including a Qatari LNG tanker.",
        "47 to 57",
    ),
    (
        "Houthi Involvement Dims Prospects for Peace",
        "Houthi involvement and escalating attacks and rhetoric between the US and Iran "
        "weakened hopes for a near-term resolution.",
        "57 to 60",
    ),
    (
        "TTF Day-Ahead Rises 11% as Strait Reopening Hopes Fade",
        "US rejection of Iranian demands dashed hopes of reopening the Strait of Hormuz. "
        "Attacks on shipping added further risk premium.",
        "58 to 68",
    ),
    (
        "Storage and Qatar LNG Risks Extend TTF Rally 9%",
        "TTF extended its rally, up 9% since Friday's close, amid winter storage concerns, "
        "QatarEnergy force majeure, and persistent geopolitical tensions.",
        "68 to 73",
    ),
    (
        "Tanker Attacks Intensify as Strait Reopening Hopes Fade",
        "US-Iran attacks intensified, with several tankers hit by projectiles in the Strait "
        "of Hormuz, further dimming hopes of a reopening.",
        "73 to 80",
    ),
])

DOWN_SIGNALS = _signals("down", [
    (
        "Iran Talks and Warmer Weather Push TTF Day-Ahead Lower",
        "Easing geopolitical risk after confirmation that Iran talks were ongoing, a broader "
        "energy sell-off, and warmer weather sent day-ahead prices lower.",
        "40 to 35, then 30",
    ),
    (
        "TTF Falls as Talks Calm Markets and Traders Take Profits",
        "Comments from Trump eased market concerns. Profit-taking added pressure after "
        "day-ahead prices reached a 13-month high.",
        "50 to 45",
    ),
    (
        "Two-Week Ceasefire and Strait Reopening Send Gas Lower",
        "A last-minute two-week ceasefire and confirmation that the Strait of Hormuz would "
        "reopen prompted a gas-market sell-off and a rally in equities.",
        "60 to 50",
    ),
    (
        "Ceasefire Optimism Drives a 13% Two-Session Drop",
        "Optimism around a ceasefire and lower demand forecasts drove day-ahead prices down "
        "13% over two sessions.",
        "50 to 45",
    ),
    (
        "Warmer Weather and Softer Demand Weigh on Gas",
        "Renewed ceasefire hopes and softer fundamentals left demand subdued as warmer weather "
        "supported robust storage injections.",
        "45 to 43",
    ),
    (
        "Peace-Deal Optimism Sends Gas Prices Down 11%",
        "Gas prices fell 11% over four sessions as a Middle East peace agreement improved "
        "sentiment, though later comments added uncertainty.",
        "46 to 41",
    ),
    (
        "Pause in Attacks Revives Hopes for Peace Talks",
        "The US paused attacks on Iran, and Iran halted regional attacks to allow peace talks "
        "to resume.",
        "60 to 55",
    ),
])


SURGE_SIGNALS = _signals("surge", [
    (
        "Emergency: Major LNG Terminal Outage Sends Gas Prices Soaring",
        "A major LNG import terminal went offline unexpectedly while storage is already low. "
        "Traders are scrambling to cover, and day-ahead prices are rising at record speed.",
        "",
    ),
    (
        "Polar Vortex and Reactor Trips Trigger Price Spike",
        "An unprecedented cold snap is driving heating demand to multi-year highs while several "
        "nuclear units tripped offline. Spot power and gas prices are spiking.",
        "",
    ),
    (
        "Pipeline Rupture Cuts Supply – Panic Buying in the Gas Market",
        "A major pipeline rupture removed a large share of pipeline flows into the region. "
        "Market participants report panic buying and a sharp jump in the risk premium.",
        "",
    ),
    (
        "Blackout Fears: Supply Margins at Critical Levels",
        "Grid operators warn that supply margins are at critical levels after simultaneous "
        "plant outages and a continent-wide heatwave. Prices are surging across the curve.",
        "",
    ),
])

CRASH_SIGNALS = _signals("crash", [
    (
        "Sudden Peace Deal Triggers Massive Sell-Off in Gas",
        "A surprise comprehensive peace agreement removed the geopolitical risk premium "
        "overnight. Traders are dumping positions and prices are collapsing.",
        "",
    ),
    (
        "Storage Overflowing: LNG Glut Crushes Prices",
        "A wave of unsold LNG cargoes arrived just as storage sites approach full capacity. "
        "Sellers are cutting offers aggressively to find buyers.",
        "",
    ),
    (
        "Record Wind and Solar Output Floods the Market",
        "Exceptional wind and solar generation combined with mild weather and weak demand is "
        "pushing wholesale power prices down sharply.",
        "",
    ),
    (
        "Demand Collapse: Industrial Shutdowns Hit Consumption",
        "A sudden drop in industrial demand and a warm spell left the market heavily oversupplied. "
        "Prices are in free fall as long positions are liquidated.",
        "",
    ),
])


def get_market_signal(scenario: str, seed: Optional[int] = None) -> MarketSignal:
    """Return one round-specific news item and three rotating weather items."""
    if scenario == "up":
        signals = UP_SIGNALS
    elif scenario == "down":
        signals = DOWN_SIGNALS
    elif scenario == "surge":
        signals = SURGE_SIGNALS
    elif scenario == "crash":
        signals = CRASH_SIGNALS
    else:
        signals = UP_SIGNALS + DOWN_SIGNALS

    if seed is None:
        signal = random.choice(signals)
        weather_cards = random.sample(WEATHER_CARDS, k=3)
    else:
        round_index = seed - 1
        signal = signals[round_index % len(signals)]
        weather_cards = [
            WEATHER_CARDS[(round_index + offset) % len(WEATHER_CARDS)]
            for offset in range(3)
        ]

    return MarketSignal(
        headline=signal.headline,
        body=signal.body,
        scenario=signal.scenario,
        cards=weather_cards,
    )


def market_signal_to_dict(signal: MarketSignal) -> Dict[str, Any]:
    """Convert a market signal to a dictionary for JSON serialization."""
    return {
        "headline": signal.headline,
        "body": signal.body,
        "scenario": signal.scenario,
        "cards": [
            {
                "type": card.type,
                "title": card.title,
                "summary": card.summary,
                "probability": card.probability,
                "value_label": card.value_label,
                "chart_type": card.chart_type,
                "values": card.values,
                "color": card.color,
            }
            for card in signal.cards
        ],
    }