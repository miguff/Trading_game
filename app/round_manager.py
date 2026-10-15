import asyncio
from datetime import datetime, timedelta
from typing import Callable, Optional

from app.game_state import GameState, RoundState, TradeRecord
from app.market_maker import MarketMaker, PricePoint
from app.pnl_engine import PnLEngine
from app.market_signals import get_market_signal, market_signal_to_dict

class RoundManager:
    SCENARIOS = ["up", "down", "oscillate"]
    PRICE_MODES = ("hard", "easy")
    SHOCK_DURATION_SECONDS = 20

    def __init__(self, game_state: GameState, broadcaster: Callable[[str, dict], None]) -> None:
        self.game_state = game_state
        self.market_maker = MarketMaker()
        self._round_task: Optional[asyncio.Task] = None
        self._broadcaster = broadcaster
        self._round_generation: int = 0  # Tracks game generation for current round

    def generate_scenario_schedule(self, total_rounds: int) -> dict:
        """
        Generate a random scenario schedule for all rounds.
        Returns a dict mapping round_number (1-indexed) to scenario.
        """
        import random
        schedule = {}
        for round_num in range(1, total_rounds + 1):
            schedule[round_num] = random.choice(self.SCENARIOS)
        return schedule

    def get_scenario_for_round(self, round_number: int) -> str:
        """
        Get the scenario for a specific round.
        Priority: admin override > scheduled scenario > random
        """
        # Check for admin override first
        if round_number in self.game_state.admin_overrides:
            return self.game_state.admin_overrides[round_number]

        # Use scheduled scenario if available
        if round_number in self.game_state.scenario_schedule:
            return self.game_state.scenario_schedule[round_number]

        # Fallback to random
        import random
        return random.choice(self.SCENARIOS)

    async def start_round(self, scenario: Optional[str] = None, scenario2: Optional[str] = None, duration_seconds: Optional[int] = None, total_rounds: Optional[int] = None, price_mode: Optional[str] = None) -> None:
        if self.game_state.round_state.is_active:
            raise RuntimeError("Round already active")

        # On the first round, allow admin to configure total rounds and duration
        if self.game_state.next_round_number == 1:
            if price_mode is not None:
                if price_mode not in self.PRICE_MODES:
                    raise ValueError("price_mode must be 'hard' or 'easy'")
                self.game_state.price_mode = price_mode
            if total_rounds is not None:
                if not isinstance(total_rounds, int) or total_rounds < 1:
                    raise ValueError("total_rounds must be an integer >= 1")
                self.game_state.total_rounds = total_rounds
            if duration_seconds is not None:
                if not isinstance(duration_seconds, int) or duration_seconds < 10:
                    raise ValueError("duration_seconds must be an integer >= 10")
                self.game_state.round_duration_seconds = duration_seconds

            # Generate scenario schedule for all rounds on first round
            if not self.game_state.scenario_schedule:
                self.game_state.scenario_schedule = self.generate_scenario_schedule(self.game_state.total_rounds)

        # Check if game is over
        if self.game_state.next_round_number > self.game_state.total_rounds:
            raise RuntimeError(f"Game over: all {self.game_state.total_rounds} rounds have been completed")

        # Determine round_start_price
        # Round 1: use default 50.0 (becomes game_start_price)
        # Later rounds: use previous round's ending price for continuous price path
        if self.game_state.next_round_number == 1:
            round_start_price = 50.0
        else:
            # Continuous price path: start from previous round's ending price
            round_start_price = self.game_state.previous_round_end_price or 50.0

        # Determine if this is the final round
        is_final_round = self.game_state.next_round_number >= self.game_state.total_rounds

        # Get scenario for this round (from parameter, override, schedule, or random)
        if scenario is None:
            scenario = self.get_scenario_for_round(self.game_state.next_round_number)

        # Validate scenario
        if scenario not in self.SCENARIOS:
            scenario = "up"  # Default fallback
        if scenario2 not in self.SCENARIOS:
            scenario2 = scenario

        # Simple fallback news - detailed market signals added in broadcast
        news = f"Round {self.game_state.next_round_number} starting with {scenario} scenario."
        duration = duration_seconds if duration_seconds is not None else self.game_state.round_duration_seconds
        target_end_price = round_start_price

        self.game_state.prepare_new_round(
            start_price=round_start_price,
            target_end_price=target_end_price,
            scenario=scenario,
            news_event=news,
            duration_seconds=duration,
            is_final_round=is_final_round,
            scenario2=scenario2,
        )

        self._round_generation = self.game_state.game_generation
        self._round_task = asyncio.create_task(self._run_round())
        await self._broadcast_round_started()

    async def _run_round(self) -> None:
        """Run a round with scenario-biased random walk price generation."""
        round_state = self.game_state.round_state
        duration_seconds = round_state.duration_seconds
        my_generation = self._round_generation
        last_phase = 1

        for tick in range(duration_seconds + 1):
            # Check if game was restarted (generation mismatch)
            if self.game_state.game_generation != my_generation:
                break

            if not round_state.is_active:
                break

            # Calculate progress (0.0 to 1.0)
            progress = tick / duration_seconds if duration_seconds > 0 else 0.0
            active_scenario, phase_number = self._phase_for_progress(round_state, progress)
            if phase_number != last_phase:
                round_state.scenario_phase_start_price = round_state.current_mid_price
                await self._broadcast_market_signal_update(progress)
                last_phase = phase_number
            next_progress = min(1.0, progress + 1 / duration_seconds)
            is_scenario_phase_end = (
                next_progress >= round_state.scenario_switch_progress
                if phase_number == 1
                else next_progress >= 1.0
            )

            # Determine the mid price for this tick
            if tick == 0:
                # Every round starts at its carried-forward start price.
                mid_price = round_state.start_price
            else:
                mid_price = self._next_mid_price(round_state, active_scenario, progress, is_scenario_phase_end)

            self._set_price(mid_price)
            await self._broadcast_price_update()

            if round_state.elapsed_seconds >= round_state.duration_seconds:
                break

            if tick < duration_seconds:  # Don't sleep after the final tick
                await asyncio.sleep(1)
                round_state.elapsed_seconds += 1

        # Only finalize if game wasn't restarted
        if self.game_state.game_generation == my_generation:
            await self.end_round()

    def _set_price(self, mid_price: float) -> None:
        round_state = self.game_state.round_state
        round_state.current_mid_price = mid_price
        for player in self.game_state.players.values():
            player.round_pnl = PnLEngine.compute_current_round_pnl(player, round_state)
        price_point = self.market_maker.create_price_point(mid_price)
        round_state.bid_price = price_point.bid
        round_state.offer_price = price_point.offer
        round_state.price_history.append(price_point)

    def cancel_active_round(self) -> None:
        """
        Cancel any active round. Called when game is restarted.
        Does not finalize P&L - just stops the round immediately.
        """
        if self._round_task and not self._round_task.done():
            self._round_task.cancel()
        self.game_state.round_state.is_active = False
        self._round_task = None

    async def pause_round(self) -> dict:
        """
        Pause the active round.
        Stops timer and price updates, preserves remaining time.
        """
        round_state = self.game_state.round_state
        if not round_state.is_active:
            raise RuntimeError("No active round to pause")
        if round_state.is_paused:
            raise RuntimeError("Round is already paused")

        # Calculate remaining seconds
        remaining = self._remaining_seconds(round_state)
        round_state.paused_remaining_seconds = remaining
        round_state.is_paused = True

        # Cancel the round task (we'll recreate on resume)
        if self._round_task and not self._round_task.done():
            self._round_task.cancel()
        self._round_task = None

        # Broadcast paused event to all clients
        await self._broadcast_round_paused(remaining)

        return {
            "status": "paused",
            "paused_at": datetime.utcnow().isoformat(),
            "remaining_seconds": remaining
        }

    async def resume_round(self) -> dict:
        """
        Resume a paused round.
        Restarts timer and price updates from paused state.
        """
        round_state = self.game_state.round_state
        if not round_state.is_active:
            raise RuntimeError("No active round to resume")
        if not round_state.is_paused:
            raise RuntimeError("Round is not paused")

        remaining = round_state.paused_remaining_seconds

        # Clear pause state
        round_state.is_paused = False

        # Update ends_at to continue from now + remaining seconds
        round_state.ends_at = datetime.utcnow() + timedelta(seconds=remaining)

        # Restart the round task with remaining time
        self._round_generation = self.game_state.game_generation
        self._round_task = asyncio.create_task(self._run_round_with_remaining(remaining))

        # Broadcast resumed event to all clients
        await self._broadcast_round_resumed(remaining)

        return {
            "status": "resumed",
            "remaining_seconds": remaining
        }

    async def _run_round_with_remaining(self, remaining_seconds: int) -> None:
        """Continue round from paused state with remaining time."""
        round_state = self.game_state.round_state
        my_generation = self._round_generation
        elapsed_before_resume = round_state.duration_seconds - remaining_seconds
        last_phase = self._phase_for_progress(
            round_state,
            elapsed_before_resume / round_state.duration_seconds if round_state.duration_seconds else 0.0,
        )[1]

        for tick in range(remaining_seconds + 1):
            # Check if game was restarted (generation mismatch)
            if self.game_state.game_generation != my_generation:
                break

            if not round_state.is_active or round_state.is_paused:
                break

            # Calculate progress (0.0 to 1.0) based on full duration
            full_duration = round_state.duration_seconds
            elapsed = full_duration - remaining_seconds + tick
            progress = elapsed / full_duration if full_duration > 0 else 0.0
            active_scenario, phase_number = self._phase_for_progress(round_state, progress)
            if phase_number != last_phase:
                round_state.scenario_phase_start_price = round_state.current_mid_price
                await self._broadcast_market_signal_update(progress)
                last_phase = phase_number
            next_progress = min(1.0, (elapsed + 1) / full_duration) if full_duration else 1.0
            is_scenario_phase_end = (
                next_progress >= round_state.scenario_switch_progress
                if phase_number == 1
                else next_progress >= 1.0
            )

            # Determine the mid price for this tick
            if tick == 0:
                # First tick after resume: use current price
                mid_price = round_state.current_mid_price
            else:
                mid_price = self._next_mid_price(round_state, active_scenario, progress, is_scenario_phase_end)

            self._set_price(mid_price)
            await self._broadcast_price_update()

            if round_state.elapsed_seconds >= round_state.duration_seconds:
                break

            if tick < remaining_seconds:  # Don't sleep after the final tick
                await asyncio.sleep(1)
                round_state.elapsed_seconds += 1

        # Only finalize if game wasn't restarted and not paused
        if (self.game_state.game_generation == my_generation and
            round_state.is_active and not round_state.is_paused):
            await self.end_round()

    async def end_round_manual(self) -> dict:
        """
        Manually end the current round.
        Uses latest mid-price as close price and runs same finalization as timer expiry.
        """
        round_state = self.game_state.round_state

        if not round_state.is_active:
            raise RuntimeError("No active round to end")

        # Use latest mid-price as close price
        close_price = round_state.current_mid_price

        # Cancel any running task
        if self._round_task and not self._round_task.done():
            self._round_task.cancel()
        self._round_task = None

        # Set close price for finalization
        round_state.current_mid_price = close_price
        round_state.last_traded_price = close_price

        # Call existing end_round logic (same as timer expiry)
        await self.end_round()
        close_price = round_state.current_mid_price

        return {
            "status": "ended",
            "round_number": round_state.round_number,
            "close_price": close_price,
            "finalized": True
        }

    def _remaining_seconds(self, round_state: RoundState) -> int:
        """Calculate remaining seconds in the round."""
        if round_state.is_paused:
            return round_state.paused_remaining_seconds
        if round_state.ends_at:
            remaining = int((round_state.ends_at - datetime.utcnow()).total_seconds())
            return max(0, remaining)
        return max(0, round_state.duration_seconds - round_state.elapsed_seconds)

    async def end_round(self) -> None:
        round_state = self.game_state.round_state
        if not round_state.is_active:
            return

        progress = (
            round_state.elapsed_seconds / round_state.duration_seconds
            if round_state.duration_seconds
            else 0.0
        )
        active_scenario, _ = self._phase_for_progress(round_state, progress)
        close_price = round_state.current_mid_price
        # After a shock the scenario's close rules would snap the price back, so skip them
        if not round_state.shock_applied:
            close_price = self.market_maker.enforce_scenario_phase_close(
                close_price,
                self.game_state.game_start_price,
                active_scenario,
                round_state.scenario_phase_start_price,
            )
            if round_state.scenario == round_state.scenario2 and round_state.scenario in self.market_maker.TREND_DIRECTION:
                close_price = self.market_maker.enforce_scenario_phase_close(
                    close_price,
                    self.game_state.game_start_price,
                    round_state.scenario,
                    round_state.start_price,
                )
        if close_price != round_state.current_mid_price:
            self._set_price(close_price)
            await self._broadcast_price_update()

        round_state.is_active = False
        round_state.shock_scenario = None
        round_state.shock_ticks_remaining = 0

        # Store the ending mid-price for the next round's start price
        self.game_state.previous_round_end_price = close_price

        # Finalize mark-to-market P&L for all players at final mid-price
        for player in self.game_state.players.values():
            PnLEngine.finalize_round(player, round_state)

        await self._broadcast_round_ended(close_price)
        self.game_state.next_round_number += 1

    def _phase_for_progress(self, round_state: RoundState, progress: float) -> tuple[str, int]:
        if progress < round_state.scenario_switch_progress:
            return round_state.scenario, 1
        return round_state.scenario2, 2

    async def trigger_shock(self, direction: str) -> dict:
        """Admin button: force an extreme price move (surge or crash) for the next SHOCK_DURATION_SECONDS."""
        scenario = {"positive": "surge", "negative": "crash"}.get(direction)
        if scenario is None:
            raise ValueError("Direction must be positive or negative")

        round_state = self.game_state.round_state
        if not round_state.is_active:
            raise RuntimeError("No active round")
        if round_state.is_paused:
            raise RuntimeError("Round is paused")
        if round_state.shock_scenario:
            raise RuntimeError("A shock is already running")

        round_state.shock_scenario = scenario
        round_state.shock_ticks_remaining = self.SHOCK_DURATION_SECONDS
        round_state.shock_start_price = round_state.current_mid_price
        round_state.shock_applied = True

        progress = (
            round_state.elapsed_seconds / round_state.duration_seconds
            if round_state.duration_seconds
            else 0.0
        )
        _, phase_number = self._phase_for_progress(round_state, progress)
        await self._broadcaster(
            "market_signal_update",
            {
                "round_number": round_state.round_number,
                "phase_number": phase_number,
                "active_scenario": scenario,
                "market_signals": market_signal_to_dict(get_market_signal(scenario)),
            },
        )
        return {"status": "shock_started", "direction": direction, "duration_seconds": self.SHOCK_DURATION_SECONDS}

    def _next_shock_price(self, round_state: RoundState) -> float:
        shock = round_state.shock_scenario
        ticks_left = round_state.shock_ticks_remaining
        game_start_price = self.game_state.game_start_price
        if self.game_state.price_mode == "easy":
            done = self.SHOCK_DURATION_SECONDS - ticks_left + 1
            price = self.market_maker.calculate_sine_mid_price(
                game_start_price=game_start_price,
                scenario=shock,
                scenario_start_price=round_state.shock_start_price,
                phase_progress=done / self.SHOCK_DURATION_SECONDS,
            )
        else:
            price = self.market_maker.calculate_next_mid_price(
                previous_mid=round_state.current_mid_price,
                game_start_price=game_start_price,
                round_start_price=round_state.start_price,
                target_end_price=round_state.target_end_price,
                scenario=shock,
                progress=0.0,
                is_final_round=round_state.is_final_round,
                scenario_start_price=round_state.shock_start_price,
                is_scenario_phase_end=ticks_left <= 1,
            )

        round_state.shock_ticks_remaining -= 1
        if round_state.shock_ticks_remaining <= 0:
            round_state.shock_scenario = None
            # The regular scenario resumes from the post-shock price
            round_state.scenario_phase_start_price = price
        return price

    def _next_mid_price(
        self,
        round_state: RoundState,
        active_scenario: str,
        progress: float,
        is_scenario_phase_end: bool,
    ) -> float:
        if round_state.shock_scenario:
            return self._next_shock_price(round_state)
        game_start_price = self.game_state.game_start_price
        if self.game_state.price_mode == "easy":
            switch = round_state.scenario_switch_progress
            if progress < switch:
                phase_progress = progress / switch if switch else 1.0
            else:
                phase_progress = (progress - switch) / (1 - switch) if switch < 1 else 1.0
            return self.market_maker.calculate_sine_mid_price(
                game_start_price=game_start_price,
                scenario=active_scenario,
                scenario_start_price=round_state.scenario_phase_start_price,
                phase_progress=phase_progress,
            )
        return self.market_maker.calculate_next_mid_price(
            previous_mid=round_state.current_mid_price,
            game_start_price=game_start_price,
            round_start_price=round_state.start_price,
            target_end_price=round_state.target_end_price,
            scenario=active_scenario,
            progress=progress,
            is_final_round=round_state.is_final_round,
            scenario_start_price=round_state.scenario_phase_start_price,
            is_scenario_phase_end=is_scenario_phase_end,
        )

    def get_market_signal_payload(self, progress: float) -> dict:
        round_state = self.game_state.round_state
        active_scenario, phase_number = self._phase_for_progress(round_state, progress)
        signal_seed = round_state.round_number + (phase_number - 1) * 3
        signal = get_market_signal(active_scenario, seed=signal_seed)
        return {
            "round_number": round_state.round_number,
            "phase_number": phase_number,
            "active_scenario": active_scenario,
            "market_signals": market_signal_to_dict(signal),
        }

    async def _broadcast_market_signal_update(self, progress: float) -> None:
        await self._broadcaster("market_signal_update", self.get_market_signal_payload(progress))

    async def _broadcast_round_started(self) -> None:
        round_state = self.game_state.round_state
        # Include player state so frontend can reset positions
        player_state = {
            player.player_id: {
                "position": player.current_position,
                "round_pnl": player.round_pnl,
                "cumulative_pnl": player.cumulative_pnl,
                "current_cash": player.current_cash,
                "expected_cash": player.expected_cash,
                "cost_basis": player.cost_basis,
                "tariff": player.tariff,
            }
            for player in self.game_state.players.values()
        }
        progress = (
            round_state.elapsed_seconds / round_state.duration_seconds
            if round_state.duration_seconds
            else 0.0
        )
        signal_payload = self.get_market_signal_payload(progress)

        await self._broadcaster(
            "round_started",
            {
                "round_number": round_state.round_number,
                "scenario": round_state.scenario,
                "scenario2": round_state.scenario2,
                "news": round_state.news_event,
                "active_scenario": signal_payload["active_scenario"],
                "phase_number": signal_payload["phase_number"],
                "market_signals": signal_payload["market_signals"],
                "start_price": round_state.start_price,
                "duration_seconds": round_state.duration_seconds,
                "remaining_seconds": self._remaining_seconds(round_state),
                "player_state": player_state,
            },
        )

    def _remaining_seconds(self, round_state: RoundState) -> int:
        if round_state.ends_at is None:
            return round_state.duration_seconds
        remaining = int((round_state.ends_at - datetime.utcnow()).total_seconds())
        return max(0, remaining)

    async def _broadcast_price_update(self) -> None:
        round_state = self.game_state.round_state
        await self._broadcaster(
            "price_update",
            {
                "bid": round_state.bid_price,
                "offer": round_state.offer_price,
                "last_traded_price": round_state.last_traded_price,
                "price_history": [
                    {"timestamp": p.timestamp.isoformat(), "mid": p.mid, "bid": p.bid, "offer": p.offer}
                    for p in round_state.price_history[-600:]  # 10 minutes for candle chart
                ],
                "remaining_seconds": self._remaining_seconds(round_state),
            },
        )

    async def _broadcast_round_ended(self, close_price: float) -> None:
        round_state = self.game_state.round_state

        # Build leaderboard (sorted by cumulative P&L)
        leaderboard_players = self.game_state.get_leaderboard()

        # Build player summaries with trade history
        player_summaries = []
        for player in self.game_state.players.values():
            # Find rank in leaderboard
            rank = next((i + 1 for i, p in enumerate(leaderboard_players) if p.player_id == player.player_id), 0)

            # Build trade history for this round
            trade_history = [
                {
                    "direction": t.direction,
                    "price": t.price,
                    "quantity": t.quantity,
                    "pnl_contribution": t.pnl_contribution,
                    "reference_price": t.cost_reference,
                    "is_auto_closeout": t.is_auto_closeout,
                    "resulting_position": t.resulting_position,
                }
                for t in player.trade_history if t.round_number == round_state.round_number
            ]

            player_summaries.append({
                "player_id": player.player_id,
                "name": player.name,
                "role": player.role,
                "round_pnl": player.round_pnl,
                "cumulative_pnl": player.cumulative_pnl,
                "final_position": player.current_position,
                "start_position": player.start_position,
                "trading_cash": round(player.current_cash, 2),
                "allocation_cash": PnLEngine.compute_allocation_cash(player),
                "cost_basis": player.cost_basis,
                "tariff": player.tariff,
                "rank": rank,
                "trade_history": trade_history,
            })

        # Sort player summaries by rank for consistent display
        player_summaries.sort(key=lambda p: p["rank"])

        # next_round_number is incremented after this broadcast, so compare the current round.
        game_over = round_state.round_number >= self.game_state.total_rounds
        payload = {
            "round_number": round_state.round_number,
            "close_price": close_price,
            "player_summary": player_summaries,
            "leaderboard": [
                {"player_id": p.player_id, "name": p.name, "role": p.role,
                 "round_pnl": p.round_pnl, "cumulative_pnl": p.cumulative_pnl, "rank": i + 1}
                for i, p in enumerate(leaderboard_players)
            ],
            "game_over": game_over,
        }
        if game_over:
            payload["settlement"] = {
                "clearing_price": close_price,
                "players": [
                    PnLEngine.compute_settlement(p, close_price) for p in leaderboard_players
                ],
            }

        await self._broadcaster("round_ended", payload)

    async def _broadcast_round_paused(self, remaining_seconds: int) -> None:
        """Broadcast round paused event to all clients."""
        round_state = self.game_state.round_state
        await self._broadcaster(
            "round_paused",
            {
                "round_number": round_state.round_number,
                "remaining_seconds": remaining_seconds,
                "paused_at": datetime.utcnow().isoformat(),
            },
        )

    async def _broadcast_round_resumed(self, remaining_seconds: int) -> None:
        """Broadcast round resumed event to all clients."""
        round_state = self.game_state.round_state
        await self._broadcaster(
            "round_resumed",
            {
                "round_number": round_state.round_number,
                "remaining_seconds": remaining_seconds,
                "resumed_at": datetime.utcnow().isoformat(),
            },
        )
