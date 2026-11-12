import numpy as np
import pandas as pd
from typing import Optional
from .base_screener_algo import BaseScreenerAlgo, Candidate
from index_regime import IndexRegime

class BullBearPennantAlgo(BaseScreenerAlgo):
    @property
    def name(self) -> str:
        return "Bull & Bear Pennant Continuation"

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

        # Look for Bullish Flagpole (sharp >1.8% move over bars -15 to -6)
        flagpole_start_price = df['close'].iloc[-15]
        flagpole_peak_price = df['close'].iloc[-6]
        flagpole_move_pct = ((flagpole_peak_price - flagpole_start_price) / flagpole_start_price) * 100.0

        if flagpole_move_pct < 1.8:
            return None

        # Look for Pennant Consolidation (contracting range over bars -6 to -1)
        pennant_bars = df.iloc[-6:-1]
        pennant_high = pennant_bars['high'].max()
        pennant_low = pennant_bars['low'].min()
        pennant_range_pct = ((pennant_high - pennant_low) / pennant_low) * 100.0

        # Pennant range must be tight (< 40% of the flagpole move)
        if pennant_range_pct > flagpole_move_pct * 0.5:
            return None

        # Breakout Trigger on current candle
        if latest_price <= pennant_high:
            return None

        signal_direction = "BULLISH"
        if idx_info['regime'] != "NEUTRAL" and idx_info['regime'] != signal_direction:
            return None

        move_potential_2d_pct = round(adr_pct * np.sqrt(2.5), 2)
        score = 70.0
        if abs(flagpole_move_pct) >= 2.5:
            score += 15.0
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
                "flagpole_move_pct": round(flagpole_move_pct, 2),
                "pennant_range_pct": round(pennant_range_pct, 2),
                "pennant_high": round(pennant_high, 2),
                "pennant_low": round(pennant_low, 2),
                "index_regime": idx_info['regime']
            }
        )
