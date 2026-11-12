import pandas as pd
from typing import Dict, Optional

STOCK_SECTOR_MAP = {
    "TATAELXSI": "NIFTY_IT",
    "KPITTECH": "NIFTY_IT",
    "COFORGE": "NIFTY_IT",
    "PERSISTENT": "NIFTY_IT",
    "PFC": "BANKNIFTY",
    "REC": "BANKNIFTY",
    "BEL": "NIFTY50",
    "HAL": "NIFTY50",
    "COALINDIA": "NIFTY_METAL",
    "NATIONALUM": "NIFTY_METAL",
    "POLYCAB": "NIFTY50",
    "DIXON": "NIFTY_IT",
    "KEI": "NIFTY50",
    "VOLTAS": "NIFTY50",
    "ESCORTS": "NIFTY_AUTO",
    "TATAPOWER": "NIFTY50",
    "BHEL": "NIFTY50",
    "GMRINFRA": "NIFTY50"
}

class IndexRegime:
    @staticmethod
    def analyze_index(index_df: Optional[pd.DataFrame]) -> Dict[str, str]:
        if index_df is None or index_df.empty or len(index_df) < 50:
            return {"regime": "NEUTRAL", "strength": "NONE"}

        df = index_df.copy()
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp').reset_index(drop=True)

        latest_price = float(df['close'].iloc[-1])
        df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
        df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()

        ema20_curr = df['ema20'].iloc[-1]
        ema50_curr = df['ema50'].iloc[-1]

        ret_1h = (latest_price - df['close'].iloc[-15]) / df['close'].iloc[-15] if len(df) >= 15 else 0.0

        if latest_price > ema20_curr > ema50_curr and ret_1h > -0.002:
            return {"regime": "BULLISH", "strength": "STRONG" if ret_1h > 0.005 else "MODERATE"}
        elif latest_price < ema20_curr < ema50_curr and ret_1h < 0.002:
            return {"regime": "BEARISH", "strength": "STRONG" if ret_1h < -0.005 else "MODERATE"}
        else:
            return {"regime": "SIDEWAYS", "strength": "NEUTRAL"}

    @staticmethod
    def is_prescreener_passed(signal_direction: str, index_df: Optional[pd.DataFrame], enable_prescreener: bool = True) -> bool:
        """
        Top-Down Sector & Index Prescreener Rule:
        "Never trade a Bullish Breakout in a Bearish Sector/Index."
        """
        if not enable_prescreener:
            return True  # Prescreener disabled

        info = IndexRegime.analyze_index(index_df)
        if signal_direction == "BULLISH" and info["regime"] == "BEARISH":
            return False  # Reject trade due to bearish sector/index drag

        return True
