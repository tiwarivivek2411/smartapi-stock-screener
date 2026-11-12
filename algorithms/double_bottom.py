import numpy as np
import pandas as pd
from typing import Optional
from .base_screener_algo import BaseScreenerAlgo, Candidate
from index_regime import IndexRegime

class DoubleBottomAlgo(BaseScreenerAlgo):
    @property
    def name(self) -> str:
        return "Double Bottom W-Pattern Reversal"

    def calculate(self, symbol: str, token: str, df: pd.DataFrame, index_df: Optional[pd.DataFrame] = None) -> Optional[Candidate]:
        if df.empty or len(df) < 50:
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

        # W-Pattern Window (past 40 bars)
        w_window = df.iloc[-40:-1]
        low1 = w_window['low'].iloc[:15].min()
        neckline_high = w_window['high'].iloc[15:25].max()
        low2 = w_window['low'].iloc[25:].min()

        # Both lows must be within 0.6% of each other
        lows_diff_pct = (abs(low1 - low2) / low1) * 100.0

        # Neckline must be at least 1.2% higher than the lows
        neckline_depth_pct = ((neckline_high - min(low1, low2)) / min(low1, low2)) * 100.0

        if not (lows_diff_pct <= 0.8 and neckline_depth_pct >= 1.0):
            return None

        # Breakout Trigger above Neckline High
        if latest_price <= neckline_high:
            return None

        signal_direction = "BULLISH"
        move_potential_2d_pct = round(adr_pct * np.sqrt(2.5), 2)

        score = 80.0
        if idx_info['regime'] == signal_direction:
            score += 15.0

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
                "low1": round(low1, 2),
                "low2": round(low2, 2),
                "neckline_high": round(neckline_high, 2),
                "index_regime": idx_info['regime']
            }
        )
