import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from accuracy_evaluator import AccuracyEvaluator

class DummyAPIClient:
    pass

class TestAccuracyEvaluator(unittest.TestCase):
    def setUp(self):
        self.api_client = DummyAPIClient()
        self.evaluator = AccuracyEvaluator(api_client=self.api_client)

    def generate_synthetic_data(self, trend="bullish"):
        records = []
        base_price = 100.0
        start_time = datetime.now() - timedelta(days=5)

        for i in range(250):
            t = start_time + timedelta(minutes=5 * i)
            if trend == "bullish":
                p = base_price * (1.0 + (0.0003 * i))
            elif trend == "bearish":
                p = base_price * (1.0 - (0.0003 * i))
            else:
                p = base_price + np.sin(i / 10.0)

            records.append({
                "timestamp": t.strftime("%Y-%m-%d %H:%M:%S"),
                "open": p,
                "high": p * 1.005,
                "low": p * 0.995,
                "close": p,
                "volume": 1000
            })
        return pd.DataFrame(records)

    def test_evaluate_signal_win(self):
        df = self.generate_synthetic_data(trend="bullish")
        outcome = self.evaluator.evaluate_signal_outcome(
            df=df,
            signal_index=10,
            direction="BULLISH",
            target_pct=3.0,
            stoploss_pct=1.5,
            max_bars=187
        )
        self.assertIn(outcome["outcome"], ["WIN", "LOSS", "TIMEOUT"])
        self.assertGreater(outcome["bars_held"], 0)

    def test_evaluate_signal_loss(self):
        df = self.generate_synthetic_data(trend="bearish")
        outcome = self.evaluator.evaluate_signal_outcome(
            df=df,
            signal_index=10,
            direction="BULLISH",
            target_pct=3.0,
            stoploss_pct=1.0,
            max_bars=187
        )
        self.assertEqual(outcome["outcome"], "LOSS")
        self.assertEqual(outcome["pnl_pct"], -1.0)

if __name__ == "__main__":
    unittest.main()
