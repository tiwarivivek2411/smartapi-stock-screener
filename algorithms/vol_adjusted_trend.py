import numpy as np
import pandas as pd
from typing import Optional
from .base_screener_algo import BaseScreenerAlgo, Candidate

class VolAdjustedTrendAlgo(BaseScreenerAlgo):
    @property
    def name(self) -> str:
        return "Vol-Adjusted ADR & Momentum Trend"

    def calculate(self, symbol: str, token: str, df: pd.DataFrame, index_df: Optional[pd.DataFrame] = None) -> Optional[Candidate]:
        if df.empty or len(df) < 50:
            return None

        df = df.copy()
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp').reset_index(drop=True)

        latest_price = float(df['close'].iloc[-1])
        if latest_price <= 0:
            return None

        # 1. 5-Minute True Range & ATR (14-period)
        high_low = df['high'] - df['low']
        high_close_prev = (df['high'] - df['close'].shift(1)).abs()
        low_close_prev = (df['low'] - df['close'].shift(1)).abs()
        tr_5m = pd.concat([high_low, high_close_prev, low_close_prev], axis=1).max(axis=1)
        atr_5m = tr_5m.rolling(window=14, min_periods=1).mean().iloc[-1]

        # 2. Daily aggregation for Average Daily Range (ADR)
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

        # 3. 5-Minute Return Volatility & Projected Move
        returns_5m = np.log(df['close'] / df['close'].shift(1)).dropna()
        std_5m = returns_5m.std()
        volatility_std_pct = (std_5m * np.sqrt(187.5)) * 100.0

        adr_projected_2d = adr_pct * np.sqrt(2.5)
        move_potential_2d_pct = round((0.5 * adr_projected_2d) + (0.5 * (volatility_std_pct * 1.5)), 2)

        # 4. Technical Trend & Momentum
        df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
        df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()

        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / (loss + 1e-9)
        rsi = 100 - (100 / (1 + rs))
        latest_rsi = rsi.iloc[-1] if not rsi.empty else 50.0

        ema20_curr = df['ema20'].iloc[-1]
        ema50_curr = df['ema50'].iloc[-1]

        if not (latest_price > ema20_curr > ema50_curr):
            return None

        signal_direction = "BULLISH"
        trend_score = 75.0
        if 50.0 <= latest_rsi <= 70.0:
            trend_score += 15.0

        min_target = self.config.get("min_potential_move_pct", 3.0)
        max_target = self.config.get("max_potential_move_pct", 10.0)

        vol_score = 0.0
        if min_target <= move_potential_2d_pct <= max_target:
            vol_score = 100.0 - abs(move_potential_2d_pct - 4.0) * 10.0
            vol_score = max(50.0, min(100.0, vol_score))

        probability_score = round((0.6 * trend_score) + (0.4 * vol_score), 2)

        if not (min_target <= move_potential_2d_pct <= max_target):
            return None

        return Candidate(
            symbol=symbol,
            token=token,
            latest_price=round(latest_price, 2),
            adr_pct=round(adr_pct, 2),
            move_potential_2d_pct=move_potential_2d_pct,
            avg_daily_volume=round(avg_daily_volume, 0),
            probability_score=probability_score,
            signal_direction=signal_direction,
            algo_name=self.name,
            metrics={
                "atr_5m": round(float(atr_5m), 2),
                "rsi_14": round(float(latest_rsi), 2),
                "ema20": round(float(ema20_curr), 2),
                "ema50": round(float(ema50_curr), 2)
            }
        )
