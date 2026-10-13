from app.game_state import GameState
from app.game_state import Player
from app.pnl_engine import PnLEngine

class TradeError(Exception):
    pass

class TradingEngine:
    def __init__(self, game_state: GameState) -> None:
        self.game_state = game_state

    def execute_trade(self, session_token: str, direction: str) -> Player:
        if direction not in ("buy", "sell"):
            raise TradeError("Invalid trade direction")

        player = self.game_state.get_player_by_token(session_token)
        if player is None:
            raise TradeError("Player session not found")

        round_state = self.game_state.round_state
        if not round_state.is_active:
            raise TradeError("No active round")

        price = round_state.offer_price if direction == "buy" else round_state.bid_price
        position_change = 1 if direction == "buy" else -1
        new_position = player.current_position + position_change
        if new_position < player.min_position or new_position > player.max_position:
            raise TradeError("Position limit exceeded")

        # Update position and cash
        player.current_position = new_position
        player.update_cash(direction, price)

        # P&L contribution against the cost basis / tariff of the lot this trade touches
        pnl_contribution, cost_reference = PnLEngine.apply_trade_to_lots(player, direction, price)

        # Record trade
        player.record_trade(
            direction=direction,
            price=price,
            quantity=1,
            round_number=round_state.round_number,
            is_auto_closeout=False,
            pnl_contribution=pnl_contribution,
            resulting_position=new_position,
            cost_reference=cost_reference,
        )

        round_state.last_traded_price = price

        # Update round P&L
        player.round_pnl = PnLEngine.compute_current_round_pnl(player, round_state)

        return player
