import numpy as np
import pandas as pd
from typing import Optional
from .base_screener_algo import BaseScreenerAlgo, Candidate
from index_regime import IndexRegime

class FallingWedgeAlgo(BaseScreenerAlgo):
    @property
    def name(self) -> str:
        return "Falling Wedge Bullish Breakout"

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

        # Wedge Window (past 30 bars)
        wedge_df = df.iloc[-30:-1]
        h1 = wedge_df['high'].iloc[:10].max()
        h2 = wedge_df['high'].iloc[10:20].max()
        h3 = wedge_df['high'].iloc[20:].max()

        l1 = wedge_df['low'].iloc[:10].min()
        l2 = wedge_df['low'].iloc[10:20].min()
        l3 = wedge_df['low'].iloc[20:].min()

        # Falling Wedge Conditions:
        # Lower Highs (h1 > h2 > h3) AND Lower Lows (l1 > l2 > l3)
        # Range is contracting ( (h1-l1) > (h3-l3) )
        is_falling_wedge = (h1 > h2 > h3) and (l1 > l2 > l3) and ((h1 - l1) > (h3 - l3))

        if not is_falling_wedge:
            return None

        # Breakout Trigger above h3 (upper trendline boundary)
        if latest_price <= h3:
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
                "upper_wedge_boundary": round(h3, 2),
                "pattern_type": "FALLING_WEDGE",
                "index_regime": idx_info['regime']
            }
        )
