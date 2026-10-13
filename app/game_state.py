from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import random
import uuid

ROLE_CYCLE = ["Generator", "Retailer", "Trader"]
ROLE_SETTINGS = {
    "Generator": {"start_position": 10, "min_position": 0, "max_position": 20, "fixed_cost_factor": 0.95, "tariff_factor": 1.0},
    "Retailer": {"start_position": -10, "min_position": -20, "max_position": 0, "fixed_cost_factor": 1.0, "tariff_factor": 1.05},
    "Trader": {"start_position": 0, "min_position": -10, "max_position": 10, "fixed_cost_factor": 1.0, "tariff_factor": 1.0},
}

@dataclass
class TradeRecord:
    direction: str  # "buy" or "sell"
    price: float
    quantity: int
    timestamp: datetime
    round_number: int = 0
    is_auto_closeout: bool = False
    pnl_contribution: float = 0.0
    resulting_position: int = 0
    cost_reference: float = 0.0  # Cost basis / tariff this trade was measured against

@dataclass
class Player:
    player_id: str
    name: str
    role: str
    session_token: str
    joined_at: datetime
    join_order: int
    start_position: int
    current_position: int
    min_position: int
    max_position: int
    current_cash: float = 0.0  # Running cash ledger (buys decrease, sells increase)
    expected_cash: float = 0.0  # Fixed obligation/revenue in EUR
    round_pnl: float = 0.0  # Current round live mark-to-market P&L
    cumulative_pnl: float = 0.0  # Sum of finalized round P&L values
    trade_history: List[TradeRecord] = field(default_factory=list)
    game_trades: List[TradeRecord] = field(default_factory=list)  # All rounds; never reset between rounds
    round_allocations: List[tuple] = field(default_factory=list)  # (round_number, round_start_price, allocated_mwh, reference_price)
    round_pnl_history: List[tuple] = field(default_factory=list)  # (round_number, realized round P&L)
    settlement_pnl: float = 0.0  # Open position settled at the clearing price after the final round
    lots: List[list] = field(default_factory=list)  # FIFO [reference_price, mwh] of Generator inventory / Retailer obligations
    connected: bool = True
    round_start_price: float = 0.0  # Store for role economics calculations
    round_opening_position: int = 0  # Position carried in before this round's allocation
    finalized_this_round: bool = False  # Prevent double-counting P&L
    cost_basis: Optional[float] = None  # Generator only: €/MWh production cost
    tariff: Optional[float] = None  # Retailer only: €/MWh customer tariff

    def reset_for_round(self, start_price: float, round_number: int) -> None:
        role_settings = ROLE_SETTINGS[self.role]
        carried_position = self.current_position if round_number > 1 else 0
        self.round_opening_position = carried_position
        self.start_position = carried_position + role_settings["start_position"]
        self.current_position = self.start_position
        if self.role == "Generator":
            self.min_position = 0
            self.max_position = carried_position + role_settings["max_position"]
        elif self.role == "Retailer":
            self.min_position = carried_position + role_settings["min_position"]
            self.max_position = 0
        else:
            self.min_position = carried_position + role_settings["min_position"]
            self.max_position = carried_position + role_settings["max_position"]
        self.trade_history = []
        self.round_pnl = 0.0
        self.current_cash = 0.0
        self.round_start_price = start_price
        self.finalized_this_round = False

        # Set role-specific economics
        if self.role == "Generator":
            self.cost_basis = round(start_price * 0.95, 2)
            self.expected_cash = round(-(self.cost_basis * 10), 2)
            self.tariff = None
        elif self.role == "Retailer":
            self.tariff = round(start_price * 1.05, 2)
            self.expected_cash = round(self.tariff * 10, 2)
            self.cost_basis = None
        else:  # Trader
            self.expected_cash = 0.0
            self.cost_basis = None
            self.tariff = None
        reference = self.cost_basis if self.cost_basis is not None else (self.tariff if self.tariff is not None else 0.0)
        self.round_allocations.append((round_number, start_price, role_settings["start_position"], reference))
        if self.role != "Trader":
            self.lots.append([reference, abs(role_settings["start_position"])])

    def update_cash(self, direction: str, price: float) -> None:
        """Update running cash ledger. Buy decreases cash, sell increases cash."""
        if direction == "buy":
            self.current_cash -= price
        else:
            self.current_cash += price

    def record_trade(self, direction: str, price: float, quantity: int, round_number: int = 0,
                     is_auto_closeout: bool = False, pnl_contribution: float = 0.0, resulting_position: int = 0,
                     cost_reference: float = 0.0) -> None:
        record = TradeRecord(
            direction=direction, price=price, quantity=quantity, timestamp=datetime.utcnow(),
            round_number=round_number, is_auto_closeout=is_auto_closeout,
            pnl_contribution=pnl_contribution, resulting_position=resulting_position,
            cost_reference=cost_reference,
        )
        self.trade_history.append(record)
        self.game_trades.append(record)

@dataclass
class PricePoint:
    timestamp: datetime
    mid: float
    bid: float
    offer: float

@dataclass
class RoundState:
    round_number: int = 0
    scenario: str = "up"
    scenario2: str = "down"
    scenario_switch_progress: float = 0.5
    scenario_phase_start_price: float = 50.0
    news_event: str = ""
    start_price: float = 50.0  # round_start_price - may differ from game_start_price
    target_end_price: float = 50.0  # target price at round end (E in the formula)
    current_mid_price: float = 50.0
    bid_price: float = 49.0
    offer_price: float = 51.0
    duration_seconds: int = 90
    started_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    is_active: bool = False
    is_paused: bool = False  # NEW: Pause state for admin controls
    paused_remaining_seconds: int = 0  # NEW: Remaining seconds when paused
    price_history: List[PricePoint] = field(default_factory=list)
    last_traded_price: Optional[float] = None
    scenario_path: List[float] = field(default_factory=list)
    elapsed_seconds: int = 0
    is_final_round: bool = False  # True if this is the last configured round

    def reset(self) -> None:
        self.round_number = 0
        self.scenario = "up"
        self.scenario2 = "down"
        self.scenario_switch_progress = 0.5
        self.scenario_phase_start_price = 50.0
        self.news_event = ""
        self.start_price = 50.0
        self.target_end_price = 50.0
        self.current_mid_price = 50.0
        self.bid_price = 49.0
        self.offer_price = 51.0
        self.duration_seconds = 90
        self.started_at = None
        self.ends_at = None
        self.is_active = False
        self.is_paused = False  # Reset pause state
        self.paused_remaining_seconds = 0  # Reset paused time
        self.price_history = []
        self.last_traded_price = None
        self.scenario_path = []
        self.elapsed_seconds = 0
        self.is_final_round = False

class GameState:
    def __init__(self) -> None:
        self.players: Dict[str, Player] = {}
        self.players_by_token: Dict[str, Player] = {}
        self.join_order: List[str] = []
        self.player_id_order: List[str] = []
        self.round_state = RoundState()
        self.next_round_number = 1
        self.total_rounds = 5  # Configurable total number of rounds
        self.round_duration_seconds = 90  # Configurable round duration
        self.game_start_price: float = 50.0  # Anchor price set at start of round 1
        self.current_price: float = 50.0  # Current game-level price (persists across rounds)
        self.previous_round_end_price: Optional[float] = None  # For carry-over between rounds
        self.scenario_schedule: Dict[int, str] = {}  # round_number -> scenario (up/down/oscillate)
        self.admin_overrides: Dict[int, str] = {}  # round_number -> admin-overridden scenario
        self.game_generation: int = 0  # Increments on each game restart to invalidate old tasks
        self.price_mode: str = "hard"  # "hard" = random walk, "easy" = sine path

    def reset(self) -> None:
        """
        Reset the entire game state to initial values.
        Called when admin restarts the game.
        """
        # Clear all players
        self.players.clear()
        self.players_by_token.clear()
        self.join_order.clear()
        self.player_id_order.clear()

        # Reset round state
        self.round_state.reset()

        # Reset game-level state
        self.next_round_number = 1
        self.total_rounds = 5
        self.round_duration_seconds = 90
        self.game_start_price = 50.0
        self.current_price = 50.0
        self.previous_round_end_price = None
        self.scenario_schedule.clear()
        self.admin_overrides.clear()
        self.price_mode = "hard"

        # Increment game generation to invalidate old round tasks
        self.game_generation += 1

    def add_player(self, name: str) -> Player:
        player_id = str(uuid.uuid4())
        token = str(uuid.uuid4())
        role_index = len(self.join_order) % len(ROLE_CYCLE)
        role = ROLE_CYCLE[role_index]
        role_settings = ROLE_SETTINGS[role]
        player = Player(
            player_id=player_id,
            name=name,
            role=role,
            session_token=token,
            joined_at=datetime.utcnow(),
            join_order=len(self.join_order) + 1,
            start_position=role_settings["start_position"],
            current_position=role_settings["start_position"],
            min_position=role_settings["min_position"],
            max_position=role_settings["max_position"],
        )
        self.players[player_id] = player
        self.players_by_token[token] = player
        self.join_order.append(player_id)
        self.player_id_order.append(player_id)
        return player

    def get_player_by_token(self, token: str) -> Optional[Player]:
        return self.players_by_token.get(token)

    def get_player_by_id(self, player_id: str) -> Optional[Player]:
        return self.players.get(player_id)

    def prepare_new_round(
        self,
        start_price: float,
        target_end_price: float,
        scenario: str,
        news_event: str,
        duration_seconds: int,
        is_final_round: bool = False,
        scenario2: Optional[str] = None,
    ) -> None:
        """
        Prepare a new round with the given parameters.

        Args:
            start_price: The round_start_price (S) for this round
            target_end_price: The target price (E) at round end
            scenario: Price scenario (up, down, oscillate)
            news_event: News text for this round
            duration_seconds: Round duration in seconds
            is_final_round: True if this is the final configured round
        """
        # On first round, store the game_start_price anchor
        if self.next_round_number == 1:
            self.game_start_price = start_price

        self.round_state.round_number = self.next_round_number
        self.round_state.scenario = scenario
        self.round_state.scenario2 = scenario2 or scenario
        self.round_state.scenario_switch_progress = random.uniform(0.4, 0.6)
        self.round_state.scenario_phase_start_price = start_price
        self.round_state.news_event = news_event
        self.round_state.start_price = start_price
        self.round_state.target_end_price = target_end_price
        self.round_state.current_mid_price = start_price
        self.round_state.duration_seconds = duration_seconds
        self.round_state.is_final_round = is_final_round
        self.round_state.started_at = datetime.utcnow()
        self.round_state.ends_at = self.round_state.started_at + timedelta(seconds=duration_seconds)
        self.round_state.is_active = True
        # NOTE: price_history is NOT reset - it persists across rounds for continuous charts
        self.round_state.last_traded_price = start_price
        self.round_state.elapsed_seconds = 0
        for player in self.players.values():
            player.reset_for_round(start_price, self.next_round_number)
        self.round_state.scenario_path = []

    def get_leaderboard(self) -> List[Player]:
        return sorted(
            self.players.values(),
            key=lambda p: (-p.cumulative_pnl, p.name.lower(), p.join_order),
        )

    def active_players(self) -> List[Player]:
        return [p for p in self.players.values() if p.connected]
