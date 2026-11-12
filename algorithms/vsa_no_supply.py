import numpy as np
import pandas as pd
from typing import Optional
from .base_screener_algo import BaseScreenerAlgo, Candidate
from index_regime import IndexRegime

class VolumeSpreadAnalysisAlgo(BaseScreenerAlgo):
    @property
    def name(self) -> str:
        return "Volume Spread Analysis (VSA No-Supply & Stopping Volume)"

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

        # 1. Primary Trend Filter: Price > 20 EMA
        df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
        curr_ema20 = df['ema20'].iloc[-1]
        if latest_price < curr_ema20:
            return None

        # 2. VSA Metrics over past 5 bars
        df['vol_ma20'] = df['volume'].rolling(20).mean()
        df['spread'] = df['high'] - df['low']
        df['avg_spread20'] = df['spread'].rolling(20).mean()
        df['close_pos'] = (df['close'] - df['low']) / (df['spread'] + 1e-9)

        curr_vol = df['volume'].iloc[-1]
        curr_vol_ma = df['vol_ma20'].iloc[-1]
        curr_spread = df['spread'].iloc[-1]
        curr_close_pos = df['close_pos'].iloc[-1]

        # VSA No-Supply Test Condition:
        # A pullback candle in the past 3 bars had volume < 60% of average (seller exhaustion),
        # followed by current candle closing in upper 40% of range with expanding volume.
        prev_3_vols = df['volume'].iloc[-4:-1]
        prev_3_vol_mas = df['vol_ma20'].iloc[-4:-1]
        has_low_volume_test = any(prev_3_vols < prev_3_vol_mas * 0.7)

        is_vsa_bullish = (has_low_volume_test and curr_close_pos >= 0.55 and curr_vol > curr_vol_ma * 1.1)

        if not is_vsa_bullish:
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
                "close_position": round(curr_close_pos, 2),
                "volume_ratio": round(curr_vol / (curr_vol_ma + 1e-9), 2),
                "index_regime": idx_info['regime']
            }
        )
