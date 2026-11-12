import numpy as np
import pandas as pd
from typing import Optional
from .base_screener_algo import BaseScreenerAlgo, Candidate
from index_regime import IndexRegime

class ChannelCompressionAlgo(BaseScreenerAlgo):
    @property
    def name(self) -> str:
        return "Rectangular Channel Box Compression"

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

        # Box Channel Window (past 20 bars)
        box_df = df.iloc[-20:-1]
        box_high = box_df['high'].max()
        box_low = box_df['low'].min()
        box_height_pct = ((box_high - box_low) / box_low) * 100.0

        # Channel height must be tight (< 1.5%)
        if box_height_pct > 1.6:
            return None

        # Breakout Trigger above Box High
        if latest_price <= box_high:
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
                "box_high": round(box_high, 2),
                "box_low": round(box_low, 2),
                "box_height_pct": round(box_height_pct, 2),
                "index_regime": idx_info['regime']
            }
        )
