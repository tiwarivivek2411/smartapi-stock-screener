import numpy as np
import pandas as pd
from typing import Optional
from .base_screener_algo import BaseScreenerAlgo, Candidate
from index_regime import IndexRegime

class SupertrendVWAPConfluenceAlgo(BaseScreenerAlgo):
    @property
    def name(self) -> str:
        return "Supertrend & VWAP Confluence"

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

        # Intraday VWAP
        df['cum_pv'] = (df['close'] * df['volume']).cumsum()
        df['cum_v'] = df['volume'].cumsum()
        df['vwap'] = df['cum_pv'] / (df['cum_v'] + 1e-9)

        curr_vwap = df['vwap'].iloc[-1]

        # ATR (10)
        high_low = df['high'] - df['low']
        high_close = (df['high'] - df['close'].shift(1)).abs()
        low_close = (df['low'] - df['close'].shift(1)).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr'] = tr.rolling(10).mean()

        # Supertrend (10, 3.0)
        multiplier = 3.0
        df['hl2'] = (df['high'] + df['low']) / 2.0
        df['basic_ub'] = df['hl2'] + (multiplier * df['atr'])
        df['basic_lb'] = df['hl2'] - (multiplier * df['atr'])

        supertrend_is_bullish = latest_price > df['basic_lb'].iloc[-1]
        price_above_vwap = latest_price >= curr_vwap

        # RSI 14 Momentum Filter
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / (loss + 1e-9)
        df['rsi'] = 100.0 - (100.0 / (1.0 + rs))
        curr_rsi = df['rsi'].iloc[-1]

        # Confluence Trigger: Supertrend Bullish + Price > VWAP + RSI > 52
        if not (supertrend_is_bullish and price_above_vwap and curr_rsi >= 52.0):
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
                "vwap": round(curr_vwap, 2),
                "rsi": round(curr_rsi, 2),
                "supertrend": "BULLISH",
                "index_regime": idx_info['regime']
            }
        )
