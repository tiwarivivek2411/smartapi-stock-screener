import numpy as np
import pandas as pd
from typing import Optional
from .base_screener_algo import BaseScreenerAlgo, Candidate

class VWAPReversionAlgo(BaseScreenerAlgo):
    @property
    def name(self) -> str:
        return "VWAP Stretch & Mean Reversion"

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

        # 2. Compute Intraday Cumulative VWAP
        latest_date = df['date'].iloc[-1]
        today_df = df[df['date'] == latest_date].copy()

        if len(today_df) < 10:
            return None

        typical_price = (today_df['high'] + today_df['low'] + today_df['close']) / 3.0
        cum_tp_vol = (typical_price * today_df['volume']).cumsum()
        cum_vol = today_df['volume'].cumsum()
        vwap = cum_tp_vol / (cum_vol + 1e-9)

        # Standard Deviation from VWAP
        vwap_diff_sq = (today_df['close'] - vwap) ** 2
        vwap_std = np.sqrt(vwap_diff_sq.cumsum() / np.arange(1, len(today_df) + 1))
        z_score = (today_df['close'] - vwap) / (vwap_std + 1e-9)

        curr_z = z_score.iloc[-1]
        prev_z = z_score.iloc[-2] if len(z_score) >= 2 else curr_z

        move_potential_2d_pct = round(adr_pct * np.sqrt(2.5), 2)

        # Check bullish reversal: stretched below -1.8 std dev and hooking back up
        is_bull_reversal = (prev_z <= -1.8 and curr_z > prev_z)
        if not is_bull_reversal:
            return None

        signal_direction = "BULLISH"

        score = 60.0
        if abs(prev_z) >= 2.2:
            score += 40.0
        elif abs(prev_z) >= 1.8:
            score += 25.0

        min_move = self.config.get("min_potential_move_pct", 3.0)
        max_move = self.config.get("max_potential_move_pct", 10.0)

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
                "vwap": round(float(vwap.iloc[-1]), 2),
                "z_score_current": round(float(curr_z), 2),
                "z_score_peak": round(float(prev_z), 2)
            }
        )
