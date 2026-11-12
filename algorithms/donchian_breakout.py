import numpy as np
import pandas as pd
from typing import Optional
from .base_screener_algo import BaseScreenerAlgo, Candidate
from index_regime import IndexRegime

class DonchianBreakoutAlgo(BaseScreenerAlgo):
    @property
    def name(self) -> str:
        return "Donchian Channel Volatility Expansion"

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

        # 20-period Donchian Channels
        df['donchian_high'] = df['high'].shift(1).rolling(20).max()
        df['donchian_low'] = df['low'].shift(1).rolling(20).min()
        df['donchian_width'] = ((df['donchian_high'] - df['donchian_low']) / df['donchian_low']) * 100.0

        curr_donchian_high = df['donchian_high'].iloc[-1]
        curr_donchian_width = df['donchian_width'].iloc[-1]

        # Donchian Width Squeeze (width < 2.0% before breakout)
        was_compressed = any(df['donchian_width'].iloc[-10:-1] <= 2.0)
        is_breakout = latest_price > curr_donchian_high

        if not (was_compressed and is_breakout):
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
                "donchian_high": round(curr_donchian_high, 2),
                "donchian_width": round(curr_donchian_width, 2),
                "index_regime": idx_info['regime']
            }
        )
