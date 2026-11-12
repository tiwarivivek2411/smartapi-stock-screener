import numpy as np
import pandas as pd
from typing import Optional
from .base_screener_algo import BaseScreenerAlgo, Candidate
from index_regime import IndexRegime

class FakeoutTrapAlgo(BaseScreenerAlgo):
    @property
    def name(self) -> str:
        return "Fail-to-Return / Liquidity Trap Reversal"

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

        if avg_daily_volume < self.config.get("min_daily_volume", 50000):
            return None

        # Key High and Low of previous 20 bars (excluding last 2 bars)
        range_bars = df.iloc[-22:-2]
        key_high = range_bars['high'].max()
        key_low = range_bars['low'].min()

        prev_candle = df.iloc[-2]
        curr_candle = df.iloc[-1]

        # False Bearish Breakdown Trap -> Go LONG / BULLISH
        is_bear_fakeout = (prev_candle['low'] < key_low) and (curr_candle['close'] > key_low) and (curr_candle['close'] > prev_candle['close'])
        if not is_bear_fakeout:
            return None

        signal_direction = "BULLISH"
        move_potential_2d_pct = round(adr_pct * np.sqrt(2.5), 2)

        score = 75.0
        if idx_info['regime'] == signal_direction:
            score += 15.0

        min_move = self.config.get("min_potential_move_pct", 2.0)
        max_move = self.config.get("max_potential_move_pct", 15.0)

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
                "breached_level": round(key_low, 2),
                "trap_type": "BEAR_TRAP_BUY",
                "index_regime": idx_info['regime']
            }
        )
