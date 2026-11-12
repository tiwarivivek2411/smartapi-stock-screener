import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from algorithms import (
    VolatilitySqueezeAlgo,
    RelativeStrengthAlgo,
    EMARibbonAlgo,
    VWAPReversionAlgo,
    VolAdjustedTrendAlgo,
    ORBSqueezeAlgo,
    BullBearPennantAlgo,
    FlatLevelTriangleAlgo,
    FakeoutTrapAlgo,
    CupAndHandleAlgo,
    VolumeSpreadAnalysisAlgo,
    SupertrendVWAPConfluenceAlgo,
    DonchianBreakoutAlgo,
    VPTSurgeAlgo,
    MACDMomentumAlgo,
    DoubleBottomAlgo,
    FallingWedgeAlgo,
    ADXTrendAlgo,
    ChannelCompressionAlgo,
    RSIRangeExpansionAlgo,
    Candidate
)

class TestAll20Algorithms(unittest.TestCase):
    def setUp(self):
        self.config = {
            "min_daily_volume": 100,
            "min_potential_move_pct": 1.0,
            "max_potential_move_pct": 20.0
        }

    def generate_synthetic_5min_data(self, base_price=100.0, num_days=5, volatility=0.01):
        records = []
        current_time = datetime.now() - timedelta(days=num_days)
        price = base_price

        for day in range(num_days):
            day_time = current_time + timedelta(days=day)
            if day_time.weekday() >= 5:
                continue

            bar_time = day_time.replace(hour=9, minute=15, second=0, microsecond=0)
            for bar in range(75):
                ret = np.random.normal(0.0005, volatility)
                open_p = price
                close_p = price * (1 + ret)
                high_p = max(open_p, close_p) * (1 + abs(np.random.normal(0, volatility * 0.5)))
                low_p = min(open_p, close_p) * (1 - abs(np.random.normal(0, volatility * 0.5)))
                volume = np.random.randint(1000, 5000)

                records.append({
                    'timestamp': bar_time.strftime("%Y-%m-%d %H:%M:%S"),
                    'open': round(open_p, 2),
                    'high': round(high_p, 2),
                    'low': round(low_p, 2),
                    'close': round(close_p, 2),
                    'volume': volume
                })
                price = close_p
                bar_time += timedelta(minutes=5)

        return pd.DataFrame(records)

    def test_all_20_algorithms_instantiation(self):
        df = self.generate_synthetic_5min_data(base_price=500.0, num_days=5, volatility=0.01)
        idx_df = self.generate_synthetic_5min_data(base_price=22000.0, num_days=5, volatility=0.003)

        algos = [
            VolatilitySqueezeAlgo(self.config),
            RelativeStrengthAlgo(self.config),
            EMARibbonAlgo(self.config),
            VWAPReversionAlgo(self.config),
            VolAdjustedTrendAlgo(self.config),
            ORBSqueezeAlgo(self.config),
            BullBearPennantAlgo(self.config),
            FlatLevelTriangleAlgo(self.config),
            FakeoutTrapAlgo(self.config),
            CupAndHandleAlgo(self.config),
            VolumeSpreadAnalysisAlgo(self.config),
            SupertrendVWAPConfluenceAlgo(self.config),
            DonchianBreakoutAlgo(self.config),
            VPTSurgeAlgo(self.config),
            MACDMomentumAlgo(self.config),
            DoubleBottomAlgo(self.config),
            FallingWedgeAlgo(self.config),
            ADXTrendAlgo(self.config),
            ChannelCompressionAlgo(self.config),
            RSIRangeExpansionAlgo(self.config)
        ]

        for algo in algos:
            candidate = algo.calculate("DIXON", "21690", df, index_df=idx_df)
            if candidate:
                self.assertIsInstance(candidate, Candidate)
                self.assertEqual(candidate.symbol, "DIXON")

if __name__ == '__main__':
    unittest.main()
