import numpy as np
import pandas as pd
from typing import Optional
from .base_screener_algo import BaseScreenerAlgo, Candidate
from index_regime import IndexRegime

class OpeningRangeBreakoutDualAlgo(BaseScreenerAlgo):
    """
    Algorithm #26: Opening Range Dual Breakout & Breakdown (Intraday Long/Short).
    Evaluates the first 15-minute high/low range (09:15 AM - 09:30 AM).

    BULLISH Long Signal:
    - Price breaks above 15m Opening Range High.
    - Price > Session VWAP.
    - Volume Surge >= 2.2x 20-bar SMA.

    BEARISH Short Signal:
    - Price breaks below 15m Opening Range Low.
    - Price < Session VWAP.
    - Volume Surge >= 2.2x 20-bar SMA on Red Candle.
    """

    @property
    def name(self) -> str:
        return "Opening Range Dual Breakout & Breakdown (Long/Short)"

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

        daily_df['range_pct'] = ((daily_df['high'] - daily_df['low']) / daily_df['open']) * 100.0
        adr_pct = daily_df['range_pct'].mean()
        avg_daily_volume = daily_df['volume'].mean()

        if avg_daily_volume < self.config.get("min_daily_volume", 10000):
            return None

        latest_date = df['date'].iloc[-1]
        session_df = df[df['date'] == latest_date].copy()

        # Need at least 3 bars in current session (15 mins) to establish Opening Range
        if len(session_df) < 4:
            return None

        orb_15m_df = session_df.iloc[:3]
        orb_high = orb_15m_df['high'].max()
        orb_low = orb_15m_df['low'].min()

        # Session VWAP
        typical_price = (session_df['high'] + session_df['low'] + session_df['close']) / 3.0
        session_df['vwap'] = (typical_price * session_df['volume']).cumsum() / (session_df['volume'].cumsum() + 1e-9)
        curr_vwap = session_df['vwap'].iloc[-1]

        # Volume Surge Filter
        df['vol_ma20'] = df['volume'].rolling(20).mean()
        curr_vol = df['volume'].iloc[-1]
        avg_vol20 = df['vol_ma20'].iloc[-1]

        if curr_vol < 1.2 * avg_vol20:
            return None

        curr_open = df['open'].iloc[-1]
        signal_direction = None

        # BULLISH Breakout above ORB High
        if latest_price > orb_high and latest_price > curr_vwap and latest_price > curr_open:
            signal_direction = "BULLISH"
        # BEARISH Breakdown below ORB Low
        elif latest_price < orb_low and latest_price < curr_vwap and latest_price < curr_open:
            signal_direction = "BEARISH"

        if not signal_direction:
            return None

        move_potential_2d_pct = round(adr_pct * 0.8, 2)
        score = 90.0
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
                "orb_high": round(orb_high, 2),
                "orb_low": round(orb_low, 2),
                "vwap": round(curr_vwap, 2),
                "volume_surge_ratio": round(curr_vol / (avg_vol20 + 1e-9), 2),
                "index_regime": idx_info['regime']
            }
        )
