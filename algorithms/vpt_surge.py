import numpy as np
import pandas as pd
from typing import Optional
from .base_screener_algo import BaseScreenerAlgo, Candidate
from index_regime import IndexRegime

class VPTSurgeAlgo(BaseScreenerAlgo):
    @property
    def name(self) -> str:
        return "Volume Price Trend (VPT) Surge"

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

        # VPT Calculation
        df['pct_change'] = df['close'].pct_change()
        df['vpt'] = (df['volume'] * df['pct_change']).fillna(0).cumsum()
        df['vpt_ma20'] = df['vpt'].rolling(20).mean()

        curr_vpt = df['vpt'].iloc[-1]
        vpt_high_20 = df['vpt'].shift(1).rolling(20).max().iloc[-1]

        df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
        curr_ema20 = df['ema20'].iloc[-1]

        # Signal: VPT reaches new 20-bar high + Price > EMA 20
        if not (curr_vpt > vpt_high_20 and latest_price > curr_ema20):
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
                "vpt": round(curr_vpt, 2),
                "vpt_high_20": round(vpt_high_20, 2),
                "index_regime": idx_info['regime']
            }
        )
