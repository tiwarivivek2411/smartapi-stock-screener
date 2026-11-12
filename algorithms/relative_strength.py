import numpy as np
import pandas as pd
from typing import Optional
from .base_screener_algo import BaseScreenerAlgo, Candidate

class RelativeStrengthAlgo(BaseScreenerAlgo):
    @property
    def name(self) -> str:
        return "Relative Strength vs Nifty Benchmark"

    def calculate(self, symbol: str, token: str, df: pd.DataFrame, index_df: Optional[pd.DataFrame] = None) -> Optional[Candidate]:
        if df.empty or len(df) < 50:
            return None

        df = df.copy()
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp').reset_index(drop=True)

        latest_price = float(df['close'].iloc[-1])
        if latest_price <= 0:
            return None

        # 1. Calculate Average Daily Range (ADR %)
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

        # 2. Compute Stock Return over past 20 bars (~1.5 hours) and 75 bars (~1 day)
        stock_ret_1d = (df['close'].iloc[-1] - df['close'].iloc[-75]) / df['close'].iloc[-75] if len(df) >= 75 else 0.0

        index_ret_1d = 0.0
        if index_df is not None and not index_df.empty:
            idx_df = index_df.copy()
            idx_df['timestamp'] = pd.to_datetime(idx_df['timestamp'])
            idx_df = idx_df.sort_values('timestamp').reset_index(drop=True)
            if len(idx_df) >= 75:
                index_ret_1d = (idx_df['close'].iloc[-1] - idx_df['close'].iloc[-75]) / idx_df['close'].iloc[-75]

        # Excess Return / RS Metric
        excess_return_pct = (stock_ret_1d - index_ret_1d) * 100.0
        move_potential_2d_pct = round(adr_pct * np.sqrt(2.5), 2)

        # Signal Direction: LONG ONLY (BULLISH)
        df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
        curr_ema20 = df['ema20'].iloc[-1]

        if excess_return_pct <= 0 or latest_price <= curr_ema20:
            return None

        signal_direction = "BULLISH"

        score = 50.0
        if abs(excess_return_pct) >= 1.5:
            score += 25.0
        if abs(excess_return_pct) >= 3.0:
            score += 25.0

        min_move = self.config.get("min_potential_move_pct", 3.0)
        max_move = self.config.get("max_potential_move_pct", 10.0)

        if score < 65.0 or not (min_move <= move_potential_2d_pct <= max_move):
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
                "stock_ret_1d_pct": round(stock_ret_1d * 100, 2),
                "index_ret_1d_pct": round(index_ret_1d * 100, 2),
                "excess_return_pct": round(excess_return_pct, 2)
            }
        )
