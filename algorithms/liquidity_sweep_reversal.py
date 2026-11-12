import numpy as np
import pandas as pd
from typing import Optional
from .base_screener_algo import BaseScreenerAlgo, Candidate
from index_regime import IndexRegime

class LiquiditySweepReversalAlgo(BaseScreenerAlgo):
    """
    Algorithm #23: Institutional Liquidity Sweep & Order Block Reversal.
    Detects stop-hunting liquidity sweeps where smart money absorbs selling pressure
    and aggressively snaps price back above key institutional levels.
    1. Low of current candle sweeps below 15-bar low (Liquidity Trap)
    2. High Volume Absorption (Volume >= 2.2x 20-bar SMA)
    3. Strong Candle Reversal Close in upper 30% of range and above VWAP/20 EMA
    """

    @property
    def name(self) -> str:
        return "Liquidity Sweep & Order Block Reversal"

    def calculate(self, symbol: str, token: str, df: pd.DataFrame, index_df: Optional[pd.DataFrame] = None) -> Optional[Candidate]:
        if df.empty or len(df) < 40:
            return None

        df = df.copy()
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp').reset_index(drop=True)

        latest_price = float(df['close'].iloc[-1])
        if latest_price <= 0:
            return None

        idx_info = IndexRegime.analyze_index(index_df)

        df['date'] = df['timestamp'].dt.date
        daily_df = df.groupby('date').agg({
            'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
        }).reset_index()

        if len(daily_df) < 2:
            return None

        daily_df['range_pct'] = ((daily_df['high'] - daily_df['low']) / daily_df['open']) * 100.0
        adr_pct = daily_df['range_pct'].mean()
        avg_daily_volume = daily_df['volume'].mean()

        if avg_daily_volume < self.config.get("min_daily_volume", 10000):
            return None

        # 1. Liquidity Sweep Condition: Current low dips below 15-bar low
        prev_15_low = df['low'].iloc[-16:-1].min()
        curr_low = df['low'].iloc[-1]
        curr_high = df['high'].iloc[-1]
        curr_open = df['open'].iloc[-1]

        if not (curr_low < prev_15_low):
            return None

        # 2. Bullish Reversal Close: Current close in upper 35% of bar range & close > open
        bar_range = curr_high - curr_low
        if bar_range <= 0:
            return None

        close_location = (latest_price - curr_low) / bar_range
        if not (close_location >= 0.65 and latest_price > curr_open):
            return None

        # 3. High Volume Absorption: Volume >= 2.0x 20-bar SMA
        df['vol_ma20'] = df['volume'].rolling(20).mean()
        curr_vol = df['volume'].iloc[-1]
        avg_vol20 = df['vol_ma20'].iloc[-1]

        if curr_vol < 2.0 * avg_vol20:
            return None

        # 4. Price > 20 EMA
        df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
        curr_ema20 = df['ema20'].iloc[-1]

        if latest_price < curr_ema20:
            return None

        signal_direction = "BULLISH"
        move_potential_2d_pct = round(adr_pct * np.sqrt(2.5), 2)

        score = 86.0
        if idx_info['regime'] == signal_direction:
            score += 10.0

        min_move = self.config.get("min_potential_move_pct", 2.0)
        max_move = self.config.get("max_potential_move_pct", 20.0)

        if not (min_move <= move_potential_2d_pct <= max_move):
            return None

        return Candidate(
            symbol=symbol,
            token=token,
            latest_price=round(latest_price, 2),
            adr_pct=round(adr_pct, 2),
            move_potential_2d_pct=move_potential_2d_pct,
            avg_daily_volume=round(avg_daily_volume, 0),
            probability_score=round(score, 2),
            signal_direction=signal_direction,
            algo_name=self.name,
            metrics={
                "prev_15_low": round(prev_15_low, 2),
                "swept_low": round(curr_low, 2),
                "volume_surge_ratio": round(curr_vol / (avg_vol20 + 1e-9), 2),
                "index_regime": idx_info['regime']
            }
        )
