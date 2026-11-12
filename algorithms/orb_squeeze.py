import numpy as np
import pandas as pd
from typing import Optional
from .base_screener_algo import BaseScreenerAlgo, Candidate
from index_regime import IndexRegime

class ORBSqueezeAlgo(BaseScreenerAlgo):
    @property
    def name(self) -> str:
        return "Opening Range Breakout (ORB + Squeeze)"

    def calculate(self, symbol: str, token: str, df: pd.DataFrame, index_df: Optional[pd.DataFrame] = None) -> Optional[Candidate]:
        if df.empty or len(df) < 50:
            return None

        df = df.copy()
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp').reset_index(drop=True)

        latest_price = float(df['close'].iloc[-1])
        if latest_price <= 0:
            return None

        # Index Regime Check
        idx_info = IndexRegime.analyze_index(index_df)

        # Calculate Average Daily Range (ADR %)
        df['date'] = df['timestamp'].dt.date
        latest_date = df['date'].iloc[-1]
        today_df = df[df['date'] == latest_date].copy().reset_index(drop=True)

        if len(today_df) < 4:
            return None

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

        # 15-Minute Opening Range (first 3 five-minute bars: 9:15 to 9:30)
        orb_high = today_df.iloc[:3]['high'].max()
        orb_low = today_df.iloc[:3]['low'].min()
        orb_range_pct = ((orb_high - orb_low) / orb_low) * 100.0

        # Current Price Breakout Check: LONG ONLY (BULLISH)
        is_bull_orb = latest_price > orb_high
        if not is_bull_orb:
            return None

        # Index Filter: Only take Bull ORB if Index is not in strong Bearish regime
        if idx_info['regime'] == "BEARISH":
            return None

        # Volume Surge confirmation on current candle
        vol_ma20 = df['volume'].rolling(20).mean().iloc[-1]
        curr_vol = df['volume'].iloc[-1]
        vol_ratio = curr_vol / (vol_ma20 + 1e-9)

        if vol_ratio < 1.5:
            return None

        move_potential_2d_pct = round(adr_pct * np.sqrt(2.5), 2)
        signal_direction = "BULLISH" if is_bull_orb else "BEARISH"

        score = 65.0
        if vol_ratio >= 2.5:
            score += 20.0
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
                "orb_high": round(orb_high, 2),
                "orb_low": round(orb_low, 2),
                "orb_range_pct": round(orb_range_pct, 2),
                "volume_ratio": round(vol_ratio, 2),
                "index_regime": idx_info['regime']
            }
        )
