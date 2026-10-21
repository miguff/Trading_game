"""News and weather signals for the energy trading game, loaded from news_pool.json (source: Trading game hírek.xlsx)."""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import json
from pathlib import Path
import random


_NEWS_POOL_PATH = Path(__file__).with_name("news_pool.json")


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


def _load_news_pool() -> Dict[str, Dict[str, Dict[str, List[str]]]]:
    """Pool layout: pool[mode][kind][scenario] -> headlines (mode easy|hard, kind news|weather)."""
    with open(_NEWS_POOL_PATH, encoding="utf-8") as pool_file:
        return json.load(pool_file)


NEWS_POOL = _load_news_pool()
SCENARIOS = ("up", "down", "oscillate")
_RISING = [1.0, 1.8, 1.6, 2.8, 3.4, 4.6, 5.2]
_FALLING = [5.2, 4.4, 4.6, 3.2, 2.6, 1.6, 1.0]
_ZIGZAG = [3.0, 4.4, 2.6, 4.4, 2.6, 4.2, 3.0]
# Illustrative weather charts whose shape follows the scenario; labels are deliberately omitted
WEATHER_CHARTS = [
    # (title en, title hu, chart type, color, series per scenario)
    ("Temperature", "Hőmérséklet", "line", "#f97316",
     {"up": _FALLING, "down": _RISING, "oscillate": _ZIGZAG}),
    ("Wind generation", "Szélerőművi termelés", "bar", "#38bdf8",
     {"up": _FALLING, "down": _RISING, "oscillate": _ZIGZAG[::-1]}),
    ("Gas demand", "Gázkereslet", "area", "#a78bfa",
     {"up": _RISING, "down": _FALLING, "oscillate": _ZIGZAG}),
]


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


def _pick(items: List[str], seed: Optional[int]) -> str:
    if seed is None:
        return random.choice(items)
    return items[(seed - 1) % len(items)]


def get_market_signal(scenario: str, seed: Optional[int] = None, mode: str = "hard") -> MarketSignal:
    """Return one news headline and one weather headline for the scenario from the mode's pool."""
    if scenario in ("surge", "crash"):
        signals = SURGE_SIGNALS if scenario == "surge" else CRASH_SIGNALS
        signal = random.choice(signals) if seed is None else signals[(seed - 1) % len(signals)]
        return MarketSignal(
            headline=signal.headline, body=signal.body, scenario=signal.scenario, cards=[]
        )

    if scenario not in SCENARIOS:
        scenario = "up"
    mode = "easy" if mode == "easy" else "hard"
    pool = NEWS_POOL[mode]
    cards = [
        ForecastCard(
            type="weather",
            title=title_hu if mode == "easy" else title_en,
            summary="",
            values=series[scenario],
            chart_type=chart_type,
            color=color,
            value_label="",
        )
        for title_en, title_hu, chart_type, color, series in WEATHER_CHARTS
    ]
    weather_label = "Időjárás" if mode == "easy" else "Weather"
    return MarketSignal(
        headline=_pick(pool["news"][scenario], seed),
        body=f"{weather_label}: {_pick(pool['weather'][scenario], seed)}",
        scenario=scenario,
        cards=cards,
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