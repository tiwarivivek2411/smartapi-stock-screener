import os
import json
import time
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from smart_api_client import SmartAPIClient
from accuracy_evaluator import AccuracyEvaluator
from index_regime import IndexRegime

def run_vcp_research():
    print("==========================================================================================================")
    print("    QUANTITATIVE RESEARCH: DESIGNING 3-5 DAY HIGH-PROBABILITY SWING BREAKOUT ALGORITHM")
    print("==========================================================================================================")
    
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
    
    with open("midcap_tokens.json", 'r') as f:
        symbol_map = json.load(f)

    interval = "FIVE_MINUTE"
    end_dt = datetime.now()
    start_dt = end_dt - timedelta(days=40)
    from_date = start_dt.strftime("%Y-%m-%d %H:%M")
    to_date = end_dt.strftime("%Y-%m-%d %H:%M")

    time.sleep(0.5)
    index_df = client.fetch_historical_data("99926000", interval, from_date, to_date)
    print(f"Loaded {len(index_df)} index candles. Analyzing stock pattern characteristics...")

    signals = []
    
    for symbol, token in symbol_map.items():
        if symbol in ["NIFTY50", "BANKNIFTY"]:
            continue

        time.sleep(0.4)  # Rate limit safety delay
        df = client.fetch_historical_data(str(token), interval, from_date, to_date)
        if df.empty or len(df) < 200:
            continue

        df = df.sort_values('timestamp').reset_index(drop=True)
        
        # Calculate daily aggregates for Volatility Contraction Pattern (VCP)
        df['date'] = pd.to_datetime(df['timestamp']).dt.date
        daily_df = df.groupby('date').agg({
            'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
        }).reset_index()

        daily_df['range_pct'] = ((daily_df['high'] - daily_df['low']) / daily_df['open']) * 100.0
        daily_df['vcp_contraction'] = daily_df['range_pct'].rolling(5).mean() / (daily_df['range_pct'].rolling(20).mean() + 1e-9)

        # Iterate 5-minute candles to find VCP + Volume Surge signals
        step = 10
        for idx in range(100, len(df) - 187, step):
            sub_df = df.iloc[:idx+1]
            sub_index = index_df.iloc[:min(idx+1, len(index_df))] if index_df is not None and not index_df.empty else None

            # 1. Price > 20 EMA and 50 EMA (Trend alignment)
            ema20 = sub_df['close'].ewm(span=20, adjust=False).mean().iloc[-1]
            ema50 = sub_df['close'].ewm(span=50, adjust=False).mean().iloc[-1]
            latest_close = sub_df['close'].iloc[-1]

            if not (latest_close > ema20 > ema50):
                continue

            # 2. Volume Surge: Current 5m volume > 2.5x 20-bar average volume
            vol20_avg = sub_df['volume'].rolling(20).mean().iloc[-1]
            curr_vol = sub_df['volume'].iloc[-1]

            if not (curr_vol >= 2.5 * vol20_avg):
                continue

            # 3. Volatility Contraction (VCP): Past 10 bars range is < 1.2%
            bar_10_high = sub_df['high'].iloc[-10:-1].max()
            bar_10_low = sub_df['low'].iloc[-10:-1].min()
            range_10_pct = ((bar_10_high - bar_10_low) / bar_10_low) * 100.0

            if range_10_pct > 1.2:
                continue

            # Prescreener check
            if IndexRegime.is_prescreener_passed("BULLISH", sub_index, enable_prescreener=True):
                # Evaluate 3-5 day move outcome (+5.0% target, -2.0% stoploss, 5 days hold)
                outcome = evaluator.evaluate_signal_outcome(
                    df=df,
                    signal_index=idx,
                    direction="BULLISH",
                    target_pct=5.0,
                    stoploss_pct=2.0,
                    max_bars=187, # ~2.5 to 3 trading days
                    use_trailing_sl=True
                )
                signals.append(outcome)

    if not signals:
        print("No signals found in research iteration.")
        return

    sig_df = pd.DataFrame(signals)
    wins = len(sig_df[sig_df['pnl_pct'] >= 4.9])
    total = len(sig_df)
    win_rate = (wins / total) * 100.0 if total > 0 else 0.0
    avg_pnl = sig_df['pnl_pct'].mean()
    profit_factor = sig_df[sig_df['pnl_pct'] > 0]['pnl_pct'].sum() / (abs(sig_df[sig_df['pnl_pct'] < 0]['pnl_pct'].sum()) + 1e-9)

    print("\n----------------------------------------------------------------------------------------------------------")
    print("  RESEARCH RESULTS: VCP INSTITUTIONAL ACCUMULATION & MULTI-DAY BREAKOUT")
    print("----------------------------------------------------------------------------------------------------------")
    print(f"Total Historical Signals: {total}")
    print(f"Win Rate (Hitting +5.0% Target in 3-5 Days): {win_rate:.2f}%")
    print(f"Average PnL per Trade: {avg_pnl:+.2f}%")
    print(f"Profit Factor: {profit_factor:.2f}")

if __name__ == "__main__":
    run_vcp_research()
