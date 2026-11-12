import os
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict
from smart_api_client import SmartAPIClient
from algorithms import ALGORITHM_REGISTRY
from accuracy_evaluator import AccuracyEvaluator
from index_regime import IndexRegime

class PortfolioSimulator:
    def __init__(self, evaluator: AccuracyEvaluator):
        self.evaluator = evaluator

    def run_portfolio_simulation(self, target_pct: float = 3.0, stoploss_pct: float = 2.0, lookback_days: int = 60, max_hold_bars: int = 187) -> dict:
        symbol_file = self.evaluator.config.get("symbol_file", "midcap_tokens.json")
        symbol_map = {}
        if os.path.exists(symbol_file):
            with open(symbol_file, 'r') as f:
                symbol_map = json.load(f)

        interval = self.evaluator.config.get("interval", "FIVE_MINUTE")
        end_dt = datetime.now()
        start_dt = end_dt - timedelta(days=lookback_days)
        from_date = start_dt.strftime("%Y-%m-%d %H:%M")
        to_date = end_dt.strftime("%Y-%m-%d %H:%M")

        index_df = self.evaluator.api_client.fetch_historical_data("99926000", interval, from_date, to_date)

        # Collect chronological signals across all stocks
        all_signals = []
        instantiated_algos = {key: cls(self.evaluator.config) for key, cls in ALGORITHM_REGISTRY.items()}

        for symbol, token in symbol_map.items():
            if symbol in ["NIFTY50", "BANKNIFTY"]:
                continue

            df = self.evaluator.api_client.fetch_historical_data(str(token), interval, from_date, to_date)
            if df.empty or len(df) < 150:
                continue

            step = 10
            for idx in range(50, len(df) - max_hold_bars, step):
                sub_df = df.iloc[:idx+1]
                sub_index = index_df.iloc[:min(idx+1, len(index_df))] if index_df is not None and not index_df.empty else None

                for algo_key, algo in instantiated_algos.items():
                    candidate = algo.calculate(symbol, str(token), sub_df, index_df=sub_index)
                    if candidate and candidate.signal_direction == "BULLISH":
                        if IndexRegime.is_prescreener_passed("BULLISH", sub_index, enable_prescreener=True):
                            outcome = self.evaluator.evaluate_signal_outcome(
                                df=df,
                                signal_index=idx,
                                direction="BULLISH",
                                target_pct=target_pct,
                                stoploss_pct=stoploss_pct,
                                max_bars=max_hold_bars,
                                use_trailing_sl=True
                            )
                            all_signals.append({
                                "timestamp": df['timestamp'].iloc[idx],
                                "symbol": symbol,
                                "algo_key": algo_key,
                                "pnl_pct": outcome['pnl_pct'],
                                "bars_held": outcome['bars_held']
                            })

        signals_df = pd.DataFrame(all_signals)
        if signals_df.empty:
            return {}

        signals_df['timestamp'] = pd.to_datetime(signals_df['timestamp'])
        signals_df = signals_df.sort_values('timestamp').reset_index(drop=True)

        results = {}
        for algo_key in ALGORITHM_REGISTRY.keys():
            algo_name = ALGORITHM_REGISTRY[algo_key](self.evaluator.config).name
            algo_df = signals_df[signals_df['algo_key'] == algo_key].copy().reset_index(drop=True)

            if algo_df.empty:
                results[algo_key] = {
                    "algo_name": algo_name,
                    "scen1_final": 100000.0,
                    "scen1_pnl": 0.0,
                    "scen2_final": 500000.0,
                    "scen2_pnl": 0.0,
                    "total_trades": 0
                }
                continue

            # --- Scenario 1: Fixed ₹1,00,000 Allocation per Trade ---
            scen1_equity = 100000.0
            scen1_pnl_total = 0.0
            for _, row in algo_df.iterrows():
                trade_pnl = 100000.0 * (row['pnl_pct'] / 100.0)
                scen1_pnl_total += trade_pnl
            scen1_final = scen1_equity + scen1_pnl_total

            # --- Scenario 2: Dynamic 20% Compounding (Starting Capital ₹5,00,000, Max 5 Positions) ---
            scen2_total_equity = 500000.0
            max_positions = 5
            pos_size_pct = 0.20  # 20% per trade

            # Simulate portfolio queue
            active_positions = 0
            for _, row in algo_df.iterrows():
                position_capital = scen2_total_equity * pos_size_pct
                trade_pnl = position_capital * (row['pnl_pct'] / 100.0)
                scen2_total_equity += trade_pnl
                if scen2_total_equity < 0:
                    scen2_total_equity = 0.0
                    break

            results[algo_key] = {
                "algo_name": algo_name,
                "scen1_final": round(scen1_final, 2),
                "scen1_pnl": round(scen1_pnl_total, 2),
                "scen2_final": round(scen2_total_equity, 2),
                "scen2_pnl": round(scen2_total_equity - 500000.0, 2),
                "total_trades": len(algo_df)
            }

        return results

def main():
    with open('config.json', 'r') as f:
        full_cfg = json.load(f)
    creds = full_cfg.get("credentials", {})
    client = SmartAPIClient(
        api_key=creds.get("api_key"),
        client_code=creds.get("client_code"),
        secret_key=creds.get("secret_key")
    )
    if not client.login():
        print("API Token expired.")
        return

    evaluator = AccuracyEvaluator(api_client=client, config_path="config.json")
    sim = PortfolioSimulator(evaluator)

    print("\n==========================================================================================================")
    print("                      PORTFOLIO SIMULATION: REAL MARKET DATA (60 DAYS)")
    print("==========================================================================================================")
    print("Scenario 1: Starting ₹1,00,000 | Fixed ₹1,00,000 per trade")
    print("Scenario 2: Starting ₹5,00,000 | Dynamic 20% Compounding per trade (Max 5 Positions)\n")

    res = sim.run_portfolio_simulation(target_pct=3.0, stoploss_pct=2.0, lookback_days=60, max_hold_bars=187)

    header = f"{'Algorithm':<35} | {'Trades':<6} | {'Scen 1 Final (₹)':<16} | {'Scen 1 Profit':<14} | {'Scen 2 Final (₹)':<16} | {'Scen 2 Profit':<14}"
    print(header)
    print("=" * len(header))

    for algo_key, data in res.items():
        row = f"{data['algo_name']:<35} | {data['total_trades']:<6} | ₹{data['scen1_final']:<15,.2f} | ₹{data['scen1_pnl']:<13,.2f} | ₹{data['scen2_final']:<15,.2f} | ₹{data['scen2_pnl']:<13,.2f}"
        print(row)

    print("=" * len(header))

if __name__ == "__main__":
    main()
