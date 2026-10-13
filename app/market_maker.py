from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import math
import random


@dataclass
class PricePoint:
    timestamp: datetime
    mid: float
    bid: float
    offer: float


class MarketMaker:
    """
    Geometric random walk with direction-biased steps.

    Up/down scenarios favor their direction in both tick probability and step
    size, so counter-trend ticks still occur but are rarer and smaller. Round
    targets and final-round flags do not force an endpoint.
    """

    TREND_UP_PROBABILITY = 0.68
    TREND_STEP_MULTIPLIER = 1.25
    COUNTER_STEP_MULTIPLIER = 0.8
    RANDOM_WALK_VOLATILITY = 0.0025
    OSCILLATION_VOLATILITY = 0.0035
    SPREAD_PERCENT = 0.01       # 1% of mid_price for bid/offer spread
    MAX_DEVIATION_PERCENT = 0.60  # Safety bounds around game_start_price
    SINE_TREND_AMPLITUDE = 0.09  # Easy mode: total up/down move per scenario phase (stronger than the random walk's ~5%)
    SINE_OSCILLATION_AMPLITUDE = 0.04  # Easy mode: peak deviation of one oscillation cycle per phase
    SINE_RIPPLE_AMPLITUDE = 0.015  # Easy mode: short-cycle volatility laid over every phase
    SINE_RIPPLE_CYCLES = 3  # Easy mode: ripple cycles per scenario phase

    def __init__(self, spread: float = 2.0) -> None:
        self.spread = spread

    def calculate_next_mid_price(
        self,
        previous_mid: float,
        game_start_price: float,
        round_start_price: float,
        target_end_price: float,
        scenario: str,
        progress: float,  # 0.0 to 1.0 (elapsed / duration)
        is_final_round: bool,
        scenario_start_price: Optional[float] = None,
        is_scenario_phase_end: bool = False,
    ) -> float:
        """
        Calculate the next mid-price using stochastic scenario-biased returns.

        Args:
            previous_mid: Current mid price (state from previous tick)
            game_start_price: Anchor price (round 1 start price)
            scenario: up, down, or oscillate
            progress: 0.0 at start, 1.0 at end
            target_end_price: Retained for compatibility; it is not an enforced endpoint.
            is_final_round: Retained for compatibility; final rounds are not snapped back.
            scenario_start_price: Opening price of the current scenario phase.
            is_scenario_phase_end: Whether this tick closes the current scenario phase.

        Returns:
            New mid-price for this tick
        """
        previous_mid = max(previous_mid, 1.0)
        if scenario == "up":
            up_probability = self.TREND_UP_PROBABILITY
        elif scenario == "down":
            up_probability = 1.0 - self.TREND_UP_PROBABILITY
        else:
            up_probability = 0.5
        volatility = (
            self.OSCILLATION_VOLATILITY
            if scenario == "oscillate"
            else self.RANDOM_WALK_VOLATILITY
        )

        step_goes_up = random.random() < up_probability
        step = abs(random.gauss(0.0, volatility))
        if scenario != "oscillate":
            with_trend = step_goes_up == (scenario == "up")
            step *= self.TREND_STEP_MULTIPLIER if with_trend else self.COUNTER_STEP_MULTIPLIER
        log_return = step if step_goes_up else -step
        next_mid = previous_mid * math.exp(log_return)

        if is_scenario_phase_end and scenario_start_price is not None:
            next_mid = self.enforce_scenario_phase_close(
                next_mid,
                game_start_price,
                scenario,
                scenario_start_price,
            )

        lower_bound = max(1.0, game_start_price * (1 - self.MAX_DEVIATION_PERCENT))
        upper_bound = game_start_price * (1 + self.MAX_DEVIATION_PERCENT)
        return round(max(lower_bound, min(upper_bound, next_mid)), 2)

    def calculate_sine_mid_price(
        self,
        game_start_price: float,
        scenario: str,
        scenario_start_price: float,
        phase_progress: float,  # 0.0 to 1.0 within the current scenario phase
    ) -> float:
        """
        Easy mode: deterministic sine path for the current scenario phase.

        up/down follow a quarter-sine trend, oscillate runs one full sine cycle and
        returns to the phase opening price. A shorter sine ripple is laid over both,
        fading to zero at the phase edges so phases stay continuous and up/down still
        close on the right side of their opening price.
        """
        phase_progress = max(0.0, min(1.0, phase_progress))
        if scenario == "up":
            factor = 1 + self.SINE_TREND_AMPLITUDE * math.sin(phase_progress * math.pi / 2)
        elif scenario == "down":
            factor = 1 - self.SINE_TREND_AMPLITUDE * math.sin(phase_progress * math.pi / 2)
        else:
            factor = 1 + self.SINE_OSCILLATION_AMPLITUDE * math.sin(phase_progress * 2 * math.pi)
        factor += (
            self.SINE_RIPPLE_AMPLITUDE
            * math.sin(phase_progress * 2 * math.pi * self.SINE_RIPPLE_CYCLES)
            * math.sin(phase_progress * math.pi)
        )
        price = scenario_start_price * factor
        if phase_progress >= 1.0:
            return self.enforce_scenario_phase_close(price, game_start_price, scenario, scenario_start_price)
        lower_bound = max(1.0, game_start_price * (1 - self.MAX_DEVIATION_PERCENT))
        upper_bound = game_start_price * (1 + self.MAX_DEVIATION_PERCENT)
        return round(max(lower_bound, min(upper_bound, price)), 2)

    def enforce_scenario_phase_close(
        self,
        price: float,
        game_start_price: float,
        scenario: str,
        scenario_start_price: float,
    ) -> float:
        if scenario == "up":
            price = max(price, scenario_start_price + 0.01)
        elif scenario == "down":
            price = min(price, scenario_start_price - 0.01)

        lower_bound = max(1.0, game_start_price * (1 - self.MAX_DEVIATION_PERCENT))
        upper_bound = game_start_price * (1 + self.MAX_DEVIATION_PERCENT)
        return round(max(lower_bound, min(upper_bound, price)), 2)

    def create_price_point(self, mid_price: float) -> PricePoint:
        """
        Create a price point with bid/offer derived from mid-price.
        Uses percentage-based spread: spread = mid_price * 1%
        """
        spread = mid_price * self.SPREAD_PERCENT
        bid = round(mid_price - spread / 2, 2)
        offer = round(mid_price + spread / 2, 2)
        return PricePoint(timestamp=datetime.utcnow(), mid=mid_price, bid=bid, offer=offer)
