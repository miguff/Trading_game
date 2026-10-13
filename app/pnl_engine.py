from typing import List, Optional
from app.game_state import Player, TradeRecord
from app.game_state import RoundState


class PnLEngine:
    """
    Round P&L engine: realized P&L against the role's cost basis / tariff.

    Round P&L = current_cash + reference_price × (current_position - start_position)
    (equals the sum of the trade P&L contributions); the open position is settled at the
    clearing price after the final round.

    Generator:
      - cost_basis = round_start_price × 0.95
      - expected_cash = -cost_basis × 10
      - start_position = +10

    Retailer:
      - tariff = round_start_price × 1.05
      - expected_cash = +tariff × 10
      - start_position = -10

    Trader:
      - expected_cash = 0
      - start_position = 0
    """

    GENERATOR_COST_FACTOR = 0.95
    RETAILER_TARIFF_FACTOR = 1.05

    @staticmethod
    def get_generator_cost_basis(round_start_price: float) -> float:
        return round(round_start_price * PnLEngine.GENERATOR_COST_FACTOR, 2)

    @staticmethod
    def get_retailer_tariff(round_start_price: float) -> float:
        return round(round_start_price * PnLEngine.RETAILER_TARIFF_FACTOR, 2)

    @staticmethod
    def compute_expected_cash(player: Player) -> float:
        """Compute expected_cash based on role and round_start_price."""
        if player.role == "Generator":
            cost_basis = PnLEngine.get_generator_cost_basis(player.round_start_price)
            return -(cost_basis * 10)
        elif player.role == "Retailer":
            tariff = PnLEngine.get_retailer_tariff(player.round_start_price)
            return tariff * 10
        else:  # Trader
            return 0.0

    @staticmethod
    def reference_price(player: Player) -> float:
        """Cost basis (Generator), tariff (Retailer) or 0 (Trader) of the current round."""
        if player.cost_basis is not None:
            return player.cost_basis
        if player.tariff is not None:
            return player.tariff
        return 0.0

    @staticmethod
    def apply_trade_to_lots(player: Player, direction: str, price: float) -> tuple[float, float]:
        """
        Update the player's FIFO lots for one MWh traded and return (pnl_contribution, cost_reference).
        Generator sells / Retailer buys consume the oldest lot at that lot's own cost basis / tariff;
        the opposite trade opens a lot at the current round's cost basis / tariff.
        """
        if player.role == "Trader":
            return (price if direction == "sell" else -price), 0.0

        current_reference = PnLEngine.reference_price(player)
        consumes = (player.role == "Generator") == (direction == "sell")
        if consumes:
            reference = current_reference
            if player.lots:
                reference = player.lots[0][0]
                player.lots[0][1] -= 1
                if player.lots[0][1] <= 0:
                    player.lots.pop(0)
        else:
            reference = current_reference
            player.lots.append([reference, 1])

        contribution = (price - reference) if direction == "sell" else (reference - price)
        return contribution, reference

    @staticmethod
    def compute_allocation_cash(player: Player) -> float:
        """Cost basis / tariff part of this round's P&L (negative = cost), i.e. round P&L minus trading cash."""
        return round(PnLEngine.compute_live_pnl(player) - player.current_cash, 2)

    @staticmethod
    def compute_live_pnl(player: Player) -> float:
        """Round P&L = sum of this round's trade P&L contributions."""
        return round(sum(t.pnl_contribution for t in player.trade_history), 2)

    @staticmethod
    def compute_settlement_pnl(player: Player, clearing_price: float) -> float:
        """Open position at game end, settled at the clearing price against each lot's own cost basis / tariff."""
        if player.role == "Trader":
            return round(clearing_price * player.current_position, 2)
        sign = 1 if player.role == "Generator" else -1
        lots_qty = sum(qty for _, qty in player.lots)
        value = sum(qty * (clearing_price - reference) for reference, qty in player.lots)
        # Positions without lots (late joiners) fall back to the current reference.
        value += (abs(player.current_position) - lots_qty) * (clearing_price - PnLEngine.reference_price(player))
        return round(sign * value, 2)

    @staticmethod
    def compute_break_even(player: Player) -> Optional[float]:
        """
        Price at which the round P&L plus the settled open position is zero.
        Returns None when position is 0.
        """
        if player.current_position == 0:
            return None
        live_pnl = PnLEngine.compute_live_pnl(player)
        lots_qty = sum(qty for _, qty in player.lots)
        if player.role == "Trader" or lots_qty == 0:
            be = PnLEngine.reference_price(player) - live_pnl / player.current_position
        else:
            sign = 1 if player.role == "Generator" else -1
            weighted_cost = sum(reference * qty for reference, qty in player.lots)
            be = (weighted_cost - live_pnl * sign) / lots_qty
        return round(be, 2)

    @staticmethod
    def compute_status_indicator(player: Player, mid_price: float) -> str:
        """
        Return a human-readable status indicator based on role and current mid-price.
        """
        break_even = PnLEngine.compute_break_even(player)
        if break_even is None:
            return "Position flat — P&L locked"

        if player.role == "Generator":
            if mid_price >= break_even:
                return "In profit zone"
            return f"Need price ≥ {break_even:.2f}"

        elif player.role == "Retailer":
            if mid_price <= break_even:
                return "In profit zone"
            return f"Need price ≤ {break_even:.2f}"

        else:  # Trader
            if player.current_position > 0 and mid_price >= break_even:
                return "In profit zone"
            elif player.current_position < 0 and mid_price <= break_even:
                return "In profit zone"
            elif player.current_position > 0:
                return f"Need price ≥ {break_even:.2f}"
            else:
                return f"Need price ≤ {break_even:.2f}"

    @staticmethod
    def compute_trade_pnl_contribution(trade: TradeRecord, round_start_price: float, role: str) -> float:
        """
        Compute the P&L contribution of a single trade.
        Used when recording the trade to store pnl_contribution in TradeRecord.

        Trader: simple cashflow P&L
          - Buy: -price (cash outflow)
          - Sell: +price (cash inflow)

        Generator: cost-basis P&L (cost = round_start_price * 0.95)
          - Sell: sell_price - cost
          - Buy: cost - buy_price

        Retailer: tariff-basis P&L (tariff = round_start_price * 1.05)
          - Buy: tariff - buy_price
          - Sell: sell_price - tariff
        """
        if role == "Trader":
            if trade.direction == "buy":
                return -trade.price
            else:  # sell
                return trade.price

        elif role == "Generator":
            cost = PnLEngine.get_generator_cost_basis(round_start_price)
            if trade.direction == "sell":
                return trade.price - cost
            else:  # buy
                return cost - trade.price

        elif role == "Retailer":
            tariff = PnLEngine.get_retailer_tariff(round_start_price)
            if trade.direction == "buy":
                return tariff - trade.price
            else:  # sell
                return trade.price - tariff

        return 0.0

    @staticmethod
    def compute_current_round_pnl(player: Player, round_state: RoundState) -> float:
        """Realized round P&L so far; it changes only when the player trades."""
        return PnLEngine.compute_live_pnl(player)

    @staticmethod
    def compute_final_round_pnl(player: Player, round_state: RoundState) -> float:
        """Final realized round P&L."""
        return PnLEngine.compute_live_pnl(player)

    @staticmethod
    def compute_settlement(player: Player, clearing_price: float) -> dict:
        """
        Game-end comparison against a "did nothing" baseline.
        Baseline: every allocated MWh is held and settled at the clearing price against the
        cost basis / tariff of the round in which it was allocated.
        Actual: realized P&L of all rounds plus the settled open position.
        """
        reference = PnLEngine.reference_price(player)
        allocations = [
            {
                "round_number": round_number,
                "allocation": allocation,
                "reference_price": round_reference,
                "value": round(allocation * (clearing_price - round_reference), 2),
            }
            for round_number, _, allocation, round_reference in player.round_allocations
        ]
        total_allocation = sum(a["allocation"] for a in allocations)
        do_nothing = round(sum(a["value"] for a in allocations), 2)
        actual = round(player.cumulative_pnl, 2)
        return {
            "player_id": player.player_id,
            "name": player.name,
            "role": player.role,
            "reference_price": reference,
            "clearing_price": clearing_price,
            "total_allocation": total_allocation,
            "allocations": allocations,
            "final_position": player.current_position,
            "rounds": [{"round_number": n, "pnl": pnl} for n, pnl in player.round_pnl_history],
            "realized_pnl": round(sum(pnl for _, pnl in player.round_pnl_history), 2),
            "settlement_pnl": player.settlement_pnl,
            "do_nothing_pnl": do_nothing,
            "actual_pnl": actual,
            "difference": round(actual - do_nothing, 2),
            "beat_market": round(actual - do_nothing, 2) > 0,
            "trades": [
                {
                    "round_number": t.round_number,
                    "direction": t.direction,
                    "price": t.price,
                    "pnl_contribution": round(t.pnl_contribution, 2),
                }
                for t in player.game_trades
            ],
        }

    @staticmethod
    def finalize_round(player: Player, round_state: RoundState) -> None:
        """
        Finalize round P&L and update cumulative P&L.
        After the final round the open position is settled at the closing price.
        The closing position carries into the next round.
        """
        if player.finalized_this_round:
            return

        final_pnl = PnLEngine.compute_final_round_pnl(player, round_state)
        player.round_pnl = final_pnl
        player.round_pnl_history.append((round_state.round_number, final_pnl))
        player.cumulative_pnl += final_pnl
        if round_state.is_final_round:
            player.settlement_pnl = PnLEngine.compute_settlement_pnl(player, round_state.current_mid_price)
            player.cumulative_pnl += player.settlement_pnl
        player.finalized_this_round = True
