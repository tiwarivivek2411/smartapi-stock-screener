import numpy as np
import pandas as pd
from typing import Optional
from .base_screener_algo import BaseScreenerAlgo, Candidate

class VolatilitySqueezeAlgo(BaseScreenerAlgo):
    @property
    def name(self) -> str:
        return "Volatility Squeeze & Volume Breakout"

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

        # 2. Bollinger Bands (20, 2)
        sma20 = df['close'].rolling(window=20).mean()
        std20 = df['close'].rolling(window=20).std()
        bb_upper = sma20 + (2.0 * std20)
        bb_lower = sma20 - (2.0 * std20)

        # 3. Keltner Channels (20, 1.5 ATR)
        high_low = df['high'] - df['low']
        high_close_prev = (df['high'] - df['close'].shift(1)).abs()
        low_close_prev = (df['low'] - df['close'].shift(1)).abs()
        tr = pd.concat([high_low, high_close_prev, low_close_prev], axis=1).max(axis=1)
        atr20 = tr.rolling(window=20).mean()
        kc_upper = sma20 + (1.5 * atr20)
        kc_lower = sma20 - (1.5 * atr20)

        # 4. Check Squeeze Condition over last 5 bars
        is_squeeze = (bb_upper.iloc[-5:] <= kc_upper.iloc[-5:]) & (bb_lower.iloc[-5:] >= kc_lower.iloc[-5:])
        squeeze_count = is_squeeze.sum()

        # 5. Volume Surge
        volume_ma20 = df['volume'].rolling(window=20).mean()
        curr_vol_ratio = df['volume'].iloc[-1] / (volume_ma20.iloc[-1] + 1e-9)

        # Projected 2-3 Day Move
        move_potential_2d_pct = round(adr_pct * np.sqrt(2.5), 2)

        # Signal Direction & Scoring: LONG ONLY (BULLISH)
        curr_close = df['close'].iloc[-1]
        curr_sma = sma20.iloc[-1]
        if curr_close < curr_sma:
            return None

        signal_direction = "BULLISH"

        score = 50.0
        if squeeze_count >= 1:
            score += 25.0
        if curr_vol_ratio >= 1.8:
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
                "squeeze_bars": int(squeeze_count),
                "volume_ratio": round(curr_vol_ratio, 2),
                "bb_width_pct": round(((bb_upper.iloc[-1] - bb_lower.iloc[-1]) / curr_close) * 100, 2)
            }
        )
