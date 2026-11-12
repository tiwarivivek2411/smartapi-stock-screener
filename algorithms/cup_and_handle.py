import numpy as np
import pandas as pd
from typing import Optional
from .base_screener_algo import BaseScreenerAlgo, Candidate
from index_regime import IndexRegime

class CupAndHandleAlgo(BaseScreenerAlgo):
    @property
    def name(self) -> str:
        return "Cup & Handle Rounding Compression"

    def calculate(self, symbol: str, token: str, df: pd.DataFrame, index_df: Optional[pd.DataFrame] = None) -> Optional[Candidate]:
        if df.empty or len(df) < 60:
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

        # Cup Formation Window (bars -45 to -10)
        cup_window = df.iloc[-45:-10]
        left_rim_high = cup_window['high'].iloc[:10].max()
        cup_bottom_low = cup_window['low'].min()
        right_rim_high = cup_window['high'].iloc[-10:].max()

        cup_depth_pct = ((left_rim_high - cup_bottom_low) / left_rim_high) * 100.0

        # Cup must be between 1.5% and 8.0% deep
        if not (1.5 <= cup_depth_pct <= 8.0):
            return None

        # Rims should be relatively equal height (within 1.0% of each other)
        rim_diff_pct = (abs(left_rim_high - right_rim_high) / left_rim_high) * 100.0
        if rim_diff_pct > 1.2:
            return None

        # Handle Formation Window (bars -10 to -1)
        handle_window = df.iloc[-10:-1]
        handle_high = handle_window['high'].max()
        handle_low = handle_window['low'].min()
        handle_depth_pct = ((right_rim_high - handle_low) / right_rim_high) * 100.0

        # Handle depth should be small (< 40% of cup depth)
        if handle_depth_pct > cup_depth_pct * 0.5:
            return None

        # Current Price Breakout Trigger above handle high
        if latest_price <= handle_high:
            return None

        signal_direction = "BULLISH"
        move_potential_2d_pct = round(adr_pct * np.sqrt(2.5), 2)

        score = 75.0
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
                "cup_depth_pct": round(cup_depth_pct, 2),
                "handle_depth_pct": round(handle_depth_pct, 2),
                "rim_level": round(right_rim_high, 2),
                "index_regime": idx_info['regime']
            }
        )
