import pandas as pd
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

@dataclass
class Candidate:
    symbol: str
    token: str
    latest_price: float
    adr_pct: float                # Average Daily Range %
    move_potential_2d_pct: float  # Projected 2-3 day move potential %
    avg_daily_volume: float
    probability_score: float      # Composite Score (0-100)
    signal_direction: str         # BULLISH, BEARISH, or NEUTRAL
    algo_name: str                # Name of algorithm generating candidate
    metrics: dict                 # Algorithm-specific metadata

class BaseScreenerAlgo(ABC):
    def __init__(self, config: dict):
        self.config = config

    @property
    @abstractmethod
    def name(self) -> str:
        """Returns the human-readable name of the algorithm."""
        pass

    @abstractmethod
    def calculate(self, symbol: str, token: str, df: pd.DataFrame, index_df: Optional[pd.DataFrame] = None) -> Optional[Candidate]:
        """
        Calculates metrics and returns Candidate if stock meets algorithm criteria, else None.
        """
        pass
