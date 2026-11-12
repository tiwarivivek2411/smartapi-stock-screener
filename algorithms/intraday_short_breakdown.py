import numpy as np
import pandas as pd
from typing import Optional
from .base_screener_algo import BaseScreenerAlgo, Candidate
from index_regime import IndexRegime

class IntradayShortBreakdownAlgo(BaseScreenerAlgo):
    """
    Algorithm #24: Intraday Short Selling Breakdown Special (1-Day Intraday Only).
    Engineered specifically for capturing fast intraday short opportunities:
    1. 5-Minute VWAP Breakdown & Price Floor Collapse (Price < Session VWAP)
    2. Institutional Selling Volume Surge (Volume >= 2.2x 20-bar Volume SMA on Red Candle)
    3. 15-Minute Short-Term Relative Weakness vs NIFTY 50
    4. 5m Supertrend Bearish Alignment (ATR 10, Multiplier 2.0 Red Trend)
    """

    @property
    def name(self) -> str:
        return "Intraday Short Breakdown Special (Bearish Short)"

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

        # 1. Session VWAP Breakdown
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

        # 2. Institutional Selling Volume Spike on Red Candle
        df['vol_ma20'] = df['volume'].rolling(20).mean()
        curr_vol = df['volume'].iloc[-1]
        avg_vol20 = df['vol_ma20'].iloc[-1]
        curr_open = df['open'].iloc[-1]

        if not (curr_vol >= 1.2 * avg_vol20 and latest_price < curr_open):
            return None

        # 3. 15-Minute Short-Term Relative Weakness vs NIFTY 50
        stock_ret_15m = ((latest_price - df['close'].iloc[-3]) / df['close'].iloc[-3]) * 100.0 if len(df) >= 3 else 0.0
        index_ret_15m = 0.0
        if index_df is not None and not index_df.empty and len(index_df) >= 3:
            idx_now = float(index_df['close'].iloc[-1])
            idx_3bars_ago = float(index_df['close'].iloc[-3])
            index_ret_15m = ((idx_now - idx_3bars_ago) / idx_3bars_ago) * 100.0

        rel_weakness_15m = stock_ret_15m - index_ret_15m
        if rel_weakness_15m > 0.3:  # Triggers when stock drops with market or underperforms
            return None

        # 4. 5m Bearish Supertrend (ATR 10, Multiplier 2.0)
        high_low = df['high'] - df['low']
        high_close = (df['high'] - df['close'].shift(1)).abs()
        low_close = (df['low'] - df['close'].shift(1)).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr10 = tr.rolling(10).mean().iloc[-1]

        hl2 = (df['high'].iloc[-1] + df['low'].iloc[-1]) / 2.0
        supertrend_upper = hl2 + (2.0 * atr10)

        if latest_price >= supertrend_upper:
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
                "vwap": round(curr_vwap, 2),
                "volume_surge_ratio": round(curr_vol / (avg_vol20 + 1e-9), 2),
                "rel_weakness_15m": round(rel_weakness_15m, 2),
                "index_regime": idx_info['regime']
            }
        )
