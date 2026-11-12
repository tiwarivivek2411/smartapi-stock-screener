import numpy as np
import pandas as pd
from typing import Optional
from .base_screener_algo import BaseScreenerAlgo, Candidate
from index_regime import IndexRegime

class IntradayGapDownContinuationAlgo(BaseScreenerAlgo):
    """
    Algorithm #28: Intraday Bearish Gap-Down & Go Short Engine.
    Detects stocks that gapped down at market open (-0.8% or lower),
    failed to recover above session VWAP, and break today's Day Low.
    """

    @property
    def name(self) -> str:
        return "Intraday Bearish Gap-Down & Go (Short Special)"

    def calculate(self, symbol: str, token: str, df: pd.DataFrame, index_df: Optional[pd.DataFrame] = None) -> Optional[Candidate]:
        if df.empty or len(df) < 30:
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

        prev_close = float(daily_df['close'].iloc[-2])
        today_open = float(daily_df['open'].iloc[-1])

        # 1. Gap-Down Check (Today's Open <= -0.8% below Yesterday's Close)
        gap_pct = ((today_open - prev_close) / prev_close) * 100.0
        if gap_pct > -0.6:  # Must be gapping down or opening weak
            return None

        daily_df['range_pct'] = ((daily_df['high'] - daily_df['low']) / daily_df['open']) * 100.0
        adr_pct = daily_df['range_pct'].mean()
        avg_daily_volume = daily_df['volume'].mean()

        if avg_daily_volume < self.config.get("min_daily_volume", 10000):
            return None

        # 2. Session VWAP Breakdown
        latest_date = df['date'].iloc[-1]
        session_df = df[df['date'] == latest_date].copy()
        if len(session_df) < 3:
            return None

        typical_price = (session_df['high'] + session_df['low'] + session_df['close']) / 3.0
        session_df['vwap'] = (typical_price * session_df['volume']).cumsum() / (session_df['volume'].cumsum() + 1e-9)
        curr_vwap = session_df['vwap'].iloc[-1]

        if latest_price >= curr_vwap:
            return None

        # 3. New Low of Day Breakdown
        session_low_before = session_df['low'].iloc[:-1].min()
        if latest_price > session_low_before:
            return None

        signal_direction = "BEARISH"
        move_potential_2d_pct = round(adr_pct * 0.8, 2)

        score = 88.0
        if idx_info['regime'] == signal_direction:
            score += 10.0

        min_move = self.config.get("min_potential_move_pct", 0.8)
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
                "gap_pct": round(gap_pct, 2),
                "vwap": round(curr_vwap, 2),
                "day_low": round(session_low_before, 2),
                "index_regime": idx_info['regime']
            }
        )
