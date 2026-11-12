import numpy as np
import pandas as pd
from typing import Optional
from .base_screener_algo import BaseScreenerAlgo, Candidate
from index_regime import IndexRegime

class ADXTrendAlgo(BaseScreenerAlgo):
    @property
    def name(self) -> str:
        return "ADX & DMI Volatile Trend Expansion"

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

        # Directional Movement & ADX (14)
        up_move = df['high'] - df['high'].shift(1)
        down_move = df['low'].shift(1) - df['low']

        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

        high_low = df['high'] - df['low']
        high_close = (df['high'] - df['close'].shift(1)).abs()
        low_close = (df['low'] - df['close'].shift(1)).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)

        tr14 = tr.rolling(14).mean()
        plus_di14 = 100.0 * (pd.Series(plus_dm).rolling(14).mean() / (tr14 + 1e-9))
        minus_di14 = 100.0 * (pd.Series(minus_dm).rolling(14).mean() / (tr14 + 1e-9))

        dx = 100.0 * (plus_di14 - minus_di14).abs() / ((plus_di14 + minus_di14) + 1e-9)
        adx14 = dx.rolling(14).mean()

        curr_adx = adx14.iloc[-1]
        curr_plus_di = plus_di14.iloc[-1]
        curr_minus_di = minus_di14.iloc[-1]

        # Trigger: ADX >= 25 (strong trend strength) AND +DI > -DI
        if not (curr_adx >= 25.0 and curr_plus_di > curr_minus_di):
            return None

        signal_direction = "BULLISH"
        move_potential_2d_pct = round(adr_pct * np.sqrt(2.5), 2)

        score = 75.0
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
                "adx": round(curr_adx, 2),
                "plus_di": round(curr_plus_di, 2),
                "minus_di": round(curr_minus_di, 2),
                "index_regime": idx_info['regime']
            }
        )
