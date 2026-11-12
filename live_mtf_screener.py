import os
import json
import time
import argparse
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List
from smart_api_client import SmartAPIClient
from algorithms import ALGORITHM_REGISTRY, Candidate
from paper_trader import MultiStrategyPaperTrader
from index_regime import IndexRegime

class LiveMTFScreener:
    def __init__(self, config_path: str = "config.json", mtf_file: str = "mtf_tokens.json"):
        self.config_path = config_path
        self.mtf_file = mtf_file
        self.config = self._load_config()
        self.api_client = self._init_api_client()
        self.paper_trader = MultiStrategyPaperTrader(initial_capital_per_strategy=500000.0)

    def _load_config(self) -> dict:
        default_cfg = {
            "interval": "FIVE_MINUTE",
            "min_potential_move_pct": 2.0,
            "target_profit_pct": 3.0,
            "stoploss_pct": 2.0,
            "max_positions": 5
        }
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    data = json.load(f)
                    default_cfg.update(data.get("screener", data))
            except Exception:
                pass
        return default_cfg

    def _init_api_client(self) -> SmartAPIClient:
        with open(self.config_path, 'r') as f:
            full_cfg = json.load(f)
        creds = full_cfg.get("credentials", {})
        client = SmartAPIClient(
            api_key=creds.get("api_key"),
            client_code=creds.get("client_code"),
            secret_key=creds.get("secret_key")
        )
        if not client.login():
            print("Notice: SmartAPI Login failed. Please verify credentials.")
        return client

    def load_mtf_tokens(self) -> Dict[str, str]:
        if os.path.exists(self.mtf_file):
            with open(self.mtf_file, 'r') as f:
                return json.load(f)
        return {"RELIANCE": "2885", "SBIN": "3045", "INFY": "1594", "TCS": "11536", "HDFCBANK": "1333"}

    def run_scan(self):
        symbol_map = self.load_mtf_tokens()
        interval = self.config.get("interval", "FIVE_MINUTE")
        end_dt = datetime.now()
        start_dt = end_dt - timedelta(days=10)
        from_date = start_dt.strftime("%Y-%m-%d %H:%M")
        to_date = end_dt.strftime("%Y-%m-%d %H:%M")

        print(f"\n==========================================================================================")
        print(f"   LIVE MULTI-MODE MTF SCREENER & PAPER TRADER ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
        print(f"==========================================================================================")
        print(f"Scanning {len(symbol_map)} liquid MTF stocks across 80 Isolated Strategy-Mode Orderbooks...")

        index_df = self.api_client.fetch_historical_data("99926000", interval, from_date, to_date)
        idx_info = IndexRegime.analyze_index(index_df)
        print(f"Current Nifty 50 Index Regime: {idx_info['regime']} (Strength: {idx_info['strength']})")

        instantiated_algos = {key: cls(self.config) for key, cls in ALGORITHM_REGISTRY.items()}
        latest_prices = {}
        detected_candidates = []

        for symbol, token in symbol_map.items():
            if symbol in ["NIFTY50", "BANKNIFTY"]:
                continue

            df = self.api_client.fetch_historical_data(str(token), interval, from_date, to_date)
            if df.empty or len(df) < 50:
                continue

            latest_price = float(df['close'].iloc[-1])
            latest_prices[symbol] = latest_price

            for algo_key, algo in instantiated_algos.items():
                candidate = algo.calculate(symbol, str(token), df, index_df=index_df)
                if candidate:
                    direction = candidate.signal_direction
                    if IndexRegime.is_prescreener_passed(direction, index_df, enable_prescreener=True):
                        detected_candidates.append(candidate)
                        self.paper_trader.execute_signal(
                            algo_key=algo_key,
                            symbol=symbol,
                            token=str(token),
                            price=latest_price,
                            direction=direction
                        )

        # Update all 80 isolated orderbooks with latest live market prices
        self.paper_trader.update_all_positions(latest_prices)

        # Display Master Multi-Strategy Dashboard
        self.paper_trader.print_master_dashboard()

        if detected_candidates:
            print(f"\n--- CANDIDATES DETECTED IN THIS SCAN ({len(detected_candidates)}) ---")
            for c in detected_candidates[:10]:
                print(f"👉 [{c.symbol}] Price: ₹{c.latest_price:.2f} | Algo: {c.algo_name} | Potential 2D Move: +{c.move_potential_2d_pct}% | Score: {c.probability_score}")

def main():
    parser = argparse.ArgumentParser(description="Live Multi-Mode MTF Screener & Paper Trader")
    parser.add_argument('--loop', action='store_true', help='Run continuous loop every 5 minutes during market hours')
    parser.add_argument('--interval-seconds', type=int, default=300, help='Loop interval in seconds (default: 300)')
    args = parser.parse_args()

    screener = LiveMTFScreener()

    if args.loop:
        print("Starting continuous live market multi-mode screening loop (Press Ctrl+C to stop)...")
        while True:
            try:
                screener.run_scan()
                print(f"\nSleeping for {args.interval_seconds} seconds until next 5-minute candle scan...")
                time.sleep(args.interval_seconds)
            except KeyboardInterrupt:
                print("\nLive screener stopped by user.")
                break
            except Exception as e:
                print(f"Notice: Error during scan loop: {e}")
                time.sleep(10)
    else:
        screener.run_scan()

if __name__ == "__main__":
    main()
