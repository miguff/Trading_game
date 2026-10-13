from dataclasses import dataclass
from datetime import datetime

@dataclass
class PlayerSession:
    player_id: str
    session_token: str
    created_at: datetime
    active: bool = True
