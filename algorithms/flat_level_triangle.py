import numpy as np
import pandas as pd
from typing import Optional
from .base_screener_algo import BaseScreenerAlgo, Candidate
from index_regime import IndexRegime

class FlatLevelTriangleAlgo(BaseScreenerAlgo):
    @property
    def name(self) -> str:
        return "Ascending & Descending Triangle (Flat Level Compression)"

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

        if avg_daily_volume < self.config.get("min_daily_volume", 50000):
            return None

        # Analyze past 30 bars
        window_df = df.iloc[-30:-1].copy()

        # Flat Resistance Level (Ascending Triangle): Highs within 0.3% of each other
        recent_highs = window_df['high'].nlargest(5)
        high_spread_pct = ((recent_highs.max() - recent_highs.min()) / recent_highs.min()) * 100.0
        flat_resistance = recent_highs.mean()

        # Higher Lows trend check
        low_t1 = window_df['low'].iloc[:10].min()
        low_t2 = window_df['low'].iloc[10:20].min()
        low_t3 = window_df['low'].iloc[20:].min()
        has_higher_lows = (low_t3 > low_t2 > low_t1)

        # Flat Support Level (Descending Triangle): Lows within 0.3% of each other
        recent_lows = window_df['low'].nsmallest(5)
        low_spread_pct = ((recent_lows.max() - recent_lows.min()) / recent_lows.min()) * 100.0
        flat_support = recent_lows.mean()

        # Lower Highs trend check
        high_t1 = window_df['high'].iloc[:10].max()
        high_t2 = window_df['high'].iloc[10:20].max()
        high_t3 = window_df['high'].iloc[20:].max()
        has_lower_highs = (high_t3 < high_t2 < high_t1)

        is_ascending_triangle = (high_spread_pct <= 0.4) and has_higher_lows
        if not is_ascending_triangle or latest_price <= flat_resistance:
            return None

        signal_direction = "BULLISH"
        if idx_info['regime'] != "NEUTRAL" and idx_info['regime'] != signal_direction:
            return None

        move_potential_2d_pct = round(adr_pct * np.sqrt(2.5), 2)
        score = 75.0
        if idx_info['regime'] == signal_direction:
            score += 15.0
        if high_spread_pct <= 0.2:
            score += 10.0

        min_move = self.config.get("min_potential_move_pct", 2.0)
        max_move = self.config.get("max_potential_move_pct", 15.0)

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
                "flat_level": round(flat_resistance, 2),
                "pattern_type": "ASCENDING_TRIANGLE",
                "index_regime": idx_info['regime']
            }
        )
