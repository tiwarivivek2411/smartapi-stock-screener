import os
import json
import argparse
import pandas as pd
from datetime import datetime, timedelta
from dataclasses import asdict
from typing import List, Dict, Optional
from smart_api_client import SmartAPIClient
from algorithms import ALGORITHM_REGISTRY, Candidate

class StockScreener:
    def __init__(self, api_client: SmartAPIClient, config_path: str = "config.json", algo_names: Optional[List[str]] = None):
        self.api_client = api_client
        self.config_path = config_path
        self.config = self._load_config()
        
        selected_algos = algo_names if algo_names else self.config.get("algorithms", ["all"])
        if "all" in selected_algos:
            self.algo_classes = list(ALGORITHM_REGISTRY.values())
        else:
            self.algo_classes = [ALGORITHM_REGISTRY[name] for name in selected_algos if name in ALGORITHM_REGISTRY]

        self.algos = [algo_cls(self.config) for algo_cls in self.algo_classes]

    def _load_config(self) -> dict:
        default_screener_config = {
            "symbol_file": "nifty50_tokens.json",
            "interval": "FIVE_MINUTE",
            "lookback_days": 10,
            "min_potential_move_pct": 3.0,
            "max_potential_move_pct": 10.0,
            "min_daily_volume": 50000,
            "output_file": "screener_results.csv",
            "algorithms": ["all"]
        }
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    data = json.load(f)
                    screener_cfg = data.get("screener", data)
                    default_screener_config.update(screener_cfg)
            except Exception as e:
                print(f"Warning: Could not parse config at {self.config_path}, using defaults. Error: {e}")
        return default_screener_config

    def load_symbols(self) -> Dict[str, str]:
        symbol_file = self.config.get("symbol_file", "nifty50_tokens.json")
        if not os.path.exists(symbol_file):
            print(f"Error: Symbol file {symbol_file} not found.")
            return {}
        try:
            with open(symbol_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error reading symbol file {symbol_file}: {e}")
            return {}

    def run(self) -> List[Candidate]:
        symbol_map = self.load_symbols()
        if not symbol_map:
            print("No symbols loaded. Aborting screening.")
            return []

        lookback_days = self.config.get("lookback_days", 10)
        interval = self.config.get("interval", "FIVE_MINUTE")

        end_dt = datetime.now()
        start_dt = end_dt - timedelta(days=lookback_days)
        from_date = start_dt.strftime("%Y-%m-%d %H:%M")
        to_date = end_dt.strftime("%Y-%m-%d %H:%M")

        print(f"\n==================================================================")
        print(f"       5-MIN MULTI-STOCK SCREENER (MODULAR QUANT ALGOS)          ")
        print(f"==================================================================")
        print(f"Scanning {len(symbol_map)} symbols ({from_date} to {to_date})...")
        print(f"Active Algorithms: {[a.name for a in self.algos]}\n")

        # Optionally fetch NIFTY benchmark data for Relative Strength algorithm
        index_df = None
        if "99926000" in symbol_map.values():
            index_df = self.api_client.fetch_historical_data("99926000", interval, from_date, to_date)

        candidates: List[Candidate] = []

        for symbol, token in symbol_map.items():
            try:
                df = self.api_client.fetch_historical_data(
                    token=str(token),
                    interval=interval,
                    from_date=from_date,
                    to_date=to_date
                )
                if df.empty:
                    continue

                for algo in self.algos:
                    candidate = algo.calculate(symbol, str(token), df, index_df=index_df)
                    if candidate:
                        candidates.append(candidate)
            except Exception as e:
                print(f"Error screening {symbol} ({token}): {e}")

        candidates.sort(key=lambda c: c.probability_score, reverse=True)
        self._output_results(candidates)
        return candidates

    def _output_results(self, candidates: List[Candidate]):
        output_file = self.config.get("output_file", "screener_results.csv")

        if not candidates:
            print("No candidates met the screening criteria across selected algorithms.")
            return

        df_out = pd.DataFrame([asdict(c) for c in candidates])
        df_out.to_csv(output_file, index=False)

        print(f"\nSCREENER RESULTS ({len(candidates)} Candidates Identified):")
        print("=" * 105)
        header = f"{'Symbol':<10} | {'Price (₹)':<9} | {'2-3D Move %':<11} | {'Direction':<9} | {'Score':<6} | {'Algorithm':<35}"
        print(header)
        print("=" * 105)
        for c in candidates:
            row = f"{c.symbol:<10} | {c.latest_price:<9.2f} | {c.move_potential_2d_pct:<11.2f} | {c.signal_direction:<9} | {c.probability_score:<6.1f} | {c.algo_name:<35}"
            print(row)
        print("=" * 105)
        print(f"Saved full results to: {output_file}\n")

def main():
    parser = argparse.ArgumentParser(description="5-Minute Stock Screener for 3-5% Moves in 2-3 Days")
    parser.add_argument('--config', default='config.json', help='Path to configuration JSON file')
    parser.add_argument('--algo', choices=list(ALGORITHM_REGISTRY.keys()) + ['all'], nargs='+', default=['all'], help='Algorithm(s) to run')
    args = parser.parse_args()

    config_path = args.config
    with open(config_path, 'r') as f:
        full_cfg = json.load(f)
    creds = full_cfg.get("credentials", {})

    client = SmartAPIClient(
        api_key=creds.get("api_key"),
        client_code=creds.get("client_code"),
        secret_key=creds.get("secret_key")
    )
    if not client.login():
        print("Authentication failed. Please verify tokens.json or login credentials.")
        return

    screener = StockScreener(api_client=client, config_path=config_path, algo_names=args.algo)
    screener.run()

if __name__ == "__main__":
    main()
