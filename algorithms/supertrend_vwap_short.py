import numpy as np
import pandas as pd
from typing import Optional
from .base_screener_algo import BaseScreenerAlgo, Candidate
from index_regime import IndexRegime

class SupertrendVWAPShortAlgo(BaseScreenerAlgo):
    """
    Algorithm #27: Supertrend & VWAP Bearish Breakdown Short Special (Intraday Bearish).
    Triggers high-probability intraday short signals when price breaks down below
    both the 5m Session VWAP and 5m Supertrend (ATR 10, Multiplier 2.0).
    """

    @property
    def name(self) -> str:
        return "Supertrend & VWAP Bearish Breakdown (Short Special)"

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

        # 1. Session VWAP
        latest_date = df['date'].iloc[-1]
        session_df = df[df['date'] == latest_date].copy()
        if len(session_df) < 3:
            return None

        typical_price = (session_df['high'] + session_df['low'] + session_df['close']) / 3.0
        session_df['vwap'] = (typical_price * session_df['volume']).cumsum() / (session_df['volume'].cumsum() + 1e-9)
        curr_vwap = session_df['vwap'].iloc[-1]

        # Price MUST be BELOW VWAP for Short
        if latest_price >= curr_vwap:
            return None

        # 2. 5m Supertrend (ATR 10, Multiplier 2.0 Upper Band Breakdown)
        high_low = df['high'] - df['low']
        high_close = (df['high'] - df['close'].shift(1)).abs()
        low_close = (df['low'] - df['close'].shift(1)).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr10 = tr.rolling(10).mean().iloc[-1]

        hl2 = (df['high'].iloc[-1] + df['low'].iloc[-1]) / 2.0
        supertrend_upper = hl2 + (2.0 * atr10)

        # Price MUST be BELOW Supertrend Upper Band
        if latest_price >= supertrend_upper:
            return None

        # 3. Volume Filter (>= 1.1x 20-bar SMA on Red Candle)
        df['vol_ma20'] = df['volume'].rolling(20).mean()
        curr_vol = df['volume'].iloc[-1]
        avg_vol20 = df['vol_ma20'].iloc[-1]
        curr_open = df['open'].iloc[-1]

        if not (curr_vol >= 1.1 * avg_vol20 and latest_price < curr_open):
            return None

        signal_direction = "BEARISH"
        move_potential_2d_pct = round(adr_pct * 0.8, 2)

        score = 86.0
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
                "vwap": round(curr_vwap, 2),
                "supertrend_upper": round(supertrend_upper, 2),
                "volume_ratio": round(curr_vol / (avg_vol20 + 1e-9), 2),
                "index_regime": idx_info['regime']
            }
        )
