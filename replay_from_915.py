import json
import os
import time
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List
from smart_api_client import SmartAPIClient
from algorithms import ALGORITHM_REGISTRY, Candidate
from paper_trader import MultiStrategyPaperTrader
from index_regime import IndexRegime

def run_replay_from_0915():
    print("==========================================================================================================")
    print("      🔄 REAL-TIME MARKET REPLAY ENGINE (REPLAYING TODAY'S SESSION FROM 09:15 AM MARKET OPEN)")
    print("==========================================================================================================")

    config_file = "config.json"
    full_cfg = {}
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            full_cfg = json.load(f)

    creds = full_cfg.get("credentials", {})
    client = SmartAPIClient(
        api_key=creds.get("api_key"),
        client_code=creds.get("client_code"),
        secret_key=creds.get("secret_key")
    )
    if not client.login():
        print("Error: SmartAPI login failed.")
        return

    with open("mtf_tokens.json", 'r') as f:
        symbol_map = json.load(f)

    today_str = datetime.now().strftime("%Y-%m-%d")
    from_date = f"{today_str} 09:15"
    to_date = datetime.now().strftime("%Y-%m-%d %H:%M")

    print(f"Fetching today's 5-minute candles from {from_date} to {to_date}...")

    # Fetch Nifty 50 Index candles
    index_df = client.fetch_historical_data("99926000", "FIVE_MINUTE", from_date, to_date)
    
    symbol_candles = {}
    for symbol, token in symbol_map.items():
        if symbol in ["NIFTY50", "BANKNIFTY"]:
            continue
        c_df = client.fetch_historical_data(token, "FIVE_MINUTE", from_date, to_date)
        if not c_df.empty:
            symbol_candles[symbol] = (token, c_df)

    if not symbol_candles:
        print("Notice: No live 5m candles returned for today yet. Using current live market dataset for replay.")
        # Load from existing daily candles
        from live_mtf_screener import LiveMTFScreener
        screener = LiveMTFScreener()
        screener.run_scan()
        return

    print(f"\nSuccessfully loaded today's 5m candles for {len(symbol_candles)} Stock & ETF symbols!")
    print("Replaying market session step-by-step from 09:15 AM IST onwards...\n")

    trader = MultiStrategyPaperTrader(initial_capital_per_strategy=500000.0)
    screener_cfg = full_cfg.get("screener", {})

    # Maximum number of 5m bars today
    sample_df = list(symbol_candles.values())[0][1]
    num_bars = len(sample_df)

    detected_candidates_total = 0

    for bar_idx in range(3, num_bars + 1):
        step_candidates = []
        bar_time = sample_df['timestamp'].iloc[bar_idx - 1]
        
        slice_index_df = index_df.iloc[:bar_idx] if not index_df.empty and len(index_df) >= bar_idx else index_df

        for symbol, (token, full_df) in symbol_candles.items():
            if len(full_df) < bar_idx:
                continue
            slice_df = full_df.iloc[:bar_idx]

            for algo_key, algo_cls in ALGORITHM_REGISTRY.items():
                algo_instance = algo_cls(screener_cfg)
                c = algo_instance.calculate(symbol, token, slice_df, slice_index_df)
                if c:
                    step_candidates.append(c)

        if step_candidates:
            detected_candidates_total += len(step_candidates)
            print(f"⏰ [Bar {bar_idx}/{num_bars} @ {bar_time}] Replay detected {len(step_candidates)} strategy signals!")
            trader.process_screener_candidates(step_candidates)

    print("\n" + "=" * 110)
    print(f"✅ REPLAY COMPLETE FROM 09:15 AM! Processed {num_bars} 5m bars today.")
    print(f"Total Strategy Signals Processed across all 168 Orderbooks: {detected_candidates_total}")
    print("=" * 110 + "\n")

    trader.print_master_dashboard()

if __name__ == "__main__":
    run_replay_from_0915()
