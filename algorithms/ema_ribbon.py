import numpy as np
import pandas as pd
from typing import Optional
from .base_screener_algo import BaseScreenerAlgo, Candidate

class EMARibbonAlgo(BaseScreenerAlgo):
    @property
    def name(self) -> str:
        return "Multi-Timeframe EMA Ribbon Alignment"

    def calculate(self, symbol: str, token: str, df: pd.DataFrame, index_df: Optional[pd.DataFrame] = None) -> Optional[Candidate]:
        if df.empty or len(df) < 60:
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

        # 2. 5-Min EMAs: 8, 21, 34, 55
        df['ema8'] = df['close'].ewm(span=8, adjust=False).mean()
        df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
        df['ema34'] = df['close'].ewm(span=34, adjust=False).mean()
        df['ema55'] = df['close'].ewm(span=55, adjust=False).mean()

        e8, e21, e34, e55 = df['ema8'].iloc[-1], df['ema21'].iloc[-1], df['ema34'].iloc[-1], df['ema55'].iloc[-1]

        is_bull_ribbon_5m = (latest_price > e8 > e21 > e34 > e55)
        if not is_bull_ribbon_5m:
            return None

        # 3. 15-Min Resampling for Timeframe Confluence
        df_15m = df.set_index('timestamp').resample('15min').agg({
            'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
        }).dropna().reset_index()

        df_15m['ema8_15m'] = df_15m['close'].ewm(span=8, adjust=False).mean()
        df_15m['ema21_15m'] = df_15m['close'].ewm(span=21, adjust=False).mean()

        e8_15m = df_15m['ema8_15m'].iloc[-1]
        e21_15m = df_15m['ema21_15m'].iloc[-1]

        is_15m_confluent = (e8_15m > e21_15m) if is_bull_ribbon_5m else (e8_15m < e21_15m)

        move_potential_2d_pct = round(adr_pct * np.sqrt(2.5), 2)
        signal_direction = "BULLISH" if is_bull_ribbon_5m else "BEARISH"

        score = 65.0
        if is_15m_confluent:
            score += 35.0

        min_move = self.config.get("min_potential_move_pct", 3.0)
        max_move = self.config.get("max_potential_move_pct", 10.0)

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
                "ema8": round(e8, 2),
                "ema21": round(e21, 2),
                "ribbon_expansion_pct": round(abs((e8 - e55) / latest_price) * 100, 2),
                "confluent_15m": is_15m_confluent
            }
        )
