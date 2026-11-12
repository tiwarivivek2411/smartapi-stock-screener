import numpy as np
import pandas as pd
from typing import Optional
from .base_screener_algo import BaseScreenerAlgo, Candidate
from index_regime import IndexRegime

class KeltnerVWAPReversionAlgo(BaseScreenerAlgo):
    """
    Algorithm #25: Keltner Channels & VWAP Dual Long/Short Reversion.
    Combines VWAP (institutional fair value anchor) with Keltner Channel volatility extremes
    and volume profile confirmation for high-probability Intraday Long AND Short calls.

    BULLISH Long Rules:
    - Price touches or dips near Lower Keltner Band while holding above session VWAP floor.
    - Volume surge >= 2.0x 20-bar SMA.

    BEARISH Short Rules:
    - Price touches or surges near Upper Keltner Band while remaining below session VWAP ceiling.
    - Volume surge >= 2.0x 20-bar SMA on Red Candle.
    """

    @property
    def name(self) -> str:
        return "Keltner Channel & VWAP Dual (Long/Short)"

    def calculate(self, symbol: str, token: str, df: pd.DataFrame, index_df: Optional[pd.DataFrame] = None) -> Optional[Candidate]:
        if df.empty or len(df) < 40:
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

        # 1. Session VWAP Calculation
        latest_date = df['date'].iloc[-1]
        session_df = df[df['date'] == latest_date].copy()
        
        if len(session_df) < 5:
            return None

        typical_price = (session_df['high'] + session_df['low'] + session_df['close']) / 3.0
        session_df['vwap'] = (typical_price * session_df['volume']).cumsum() / (session_df['volume'].cumsum() + 1e-9)
        curr_vwap = session_df['vwap'].iloc[-1]

        # 2. Keltner Channels (20-bar EMA + 2.0 * ATR 10)
        df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
        high_low = df['high'] - df['low']
        high_close = (df['high'] - df['close'].shift(1)).abs()
        low_close = (df['low'] - df['close'].shift(1)).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr10 = tr.rolling(10).mean()

        upper_keltner = (df['ema20'] + (2.0 * atr10)).iloc[-1]
        lower_keltner = (df['ema20'] - (2.0 * atr10)).iloc[-1]

        # 3. Volume Spike Filter
        df['vol_ma20'] = df['volume'].rolling(20).mean()
        curr_vol = df['volume'].iloc[-1]
        avg_vol20 = df['vol_ma20'].iloc[-1]

        if curr_vol < 1.8 * avg_vol20:
            return None

        curr_low = df['low'].iloc[-1]
        curr_high = df['high'].iloc[-1]
        curr_open = df['open'].iloc[-1]

        signal_direction = None

        # BULLISH Long Condition: Price near lower Keltner band + Price > VWAP
        if curr_low <= lower_keltner * 1.002 and latest_price > curr_vwap:
            signal_direction = "BULLISH"
        # BEARISH Short Condition: Price near upper Keltner band + Price < VWAP
        elif curr_high >= upper_keltner * 0.998 and latest_price < curr_vwap:
            signal_direction = "BEARISH"

        if not signal_direction:
            return None

        move_potential_2d_pct = round(adr_pct * 0.85, 2)
        score = 88.0
        if idx_info['regime'] == signal_direction:
            score += 10.0

        min_move = self.config.get("min_potential_move_pct", 1.5)
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
                "upper_keltner": round(upper_keltner, 2),
                "lower_keltner": round(lower_keltner, 2),
                "volume_surge_ratio": round(curr_vol / (avg_vol20 + 1e-9), 2),
                "index_regime": idx_info['regime']
            }
        )
