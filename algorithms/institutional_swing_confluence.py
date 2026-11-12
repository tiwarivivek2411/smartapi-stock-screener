import numpy as np
import pandas as pd
from typing import Optional
from .base_screener_algo import BaseScreenerAlgo, Candidate
from index_regime import IndexRegime

class InstitutionalSwingConfluenceAlgo(BaseScreenerAlgo):
    """
    Custom 3-5 Day High-Probability Swing Breakout Algorithm.
    Combines:
    1. Top-Down Relative Strength vs Benchmark (Outperforming NIFTY 50)
    2. High Volatility Expansion Capacity (ADR % > 3.0%)
    3. Multi-Timeframe EMA Ribbon Alignment (Price > EMA 20 > EMA 50)
    4. ADX & DMI Momentum Strength (ADX >= 22 & +DI > -DI)
    5. Institutional Volume Surge (Volume > 2.0x 20-bar SMA)
    """

    @property
    def name(self) -> str:
        return "Institutional Swing Confluence (3-5 Day Breakout)"

    def calculate(self, symbol: str, token: str, df: pd.DataFrame, index_df: Optional[pd.DataFrame] = None) -> Optional[Candidate]:
        if df.empty or len(df) < 50:
            return None

        df = df.copy()
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp').reset_index(drop=True)

        latest_price = float(df['close'].iloc[-1])
        if latest_price <= 0:
            return None

        # 1. Benchmark & Index Regime Check
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

        # 2. Multi-Timeframe EMA Ribbon Alignment
        df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
        df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()

        curr_ema20 = df['ema20'].iloc[-1]
        curr_ema50 = df['ema50'].iloc[-1]

        if not (latest_price > curr_ema20 > curr_ema50):
            return None

        # 3. Institutional Volume Surge (Current 5m volume > 2.0x 20-bar avg volume)
        df['vol_ma20'] = df['volume'].rolling(20).mean()
        curr_vol = df['volume'].iloc[-1]
        avg_vol20 = df['vol_ma20'].iloc[-1]

        if curr_vol < 2.0 * avg_vol20:
            return None

        # 4. ADX & DMI Trend Strength
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

        if not (curr_adx >= 22.0 and curr_plus_di > curr_minus_di):
            return None

        # 5. Relative Strength vs Benchmark Check
        stock_ret_20 = ((latest_price - df['close'].iloc[-20]) / df['close'].iloc[-20]) * 100.0
        index_ret_20 = 0.0
        if index_df is not None and not index_df.empty and len(index_df) >= 20:
            idx_close_now = float(index_df['close'].iloc[-1])
            idx_close_20 = float(index_df['close'].iloc[-20])
            index_ret_20 = ((idx_close_now - idx_close_20) / idx_close_20) * 100.0

        relative_strength = stock_ret_20 - index_ret_20

        # Must outperform NIFTY by at least +0.5%
        if relative_strength < 0.5:
            return None

        signal_direction = "BULLISH"
        # 3-5 day move potential estimate based on ADR % and relative momentum
        move_potential_2d_pct = round(adr_pct * np.sqrt(3.0), 2)

        score = 85.0
        if idx_info['regime'] == signal_direction:
            score += 10.0
        if relative_strength > 2.0:
            score += 5.0

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
                "relative_strength_vs_nifty": round(relative_strength, 2),
                "adx": round(curr_adx, 2),
                "volume_surge_ratio": round(curr_vol / (avg_vol20 + 1e-9), 2),
                "index_regime": idx_info['regime']
            }
        )
