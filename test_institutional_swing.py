import json
import time
import pandas as pd
from datetime import datetime, timedelta
from smart_api_client import SmartAPIClient
from accuracy_evaluator import AccuracyEvaluator
from algorithms import InstitutionalSwingConfluenceAlgo
from index_regime import IndexRegime

def run_60day_backtest():
    print("==========================================================================================================")
    print("  60-DAY HISTORICAL BACKTEST: INSTITUTIONAL SWING CONFLUENCE (3-5 DAY BREAKOUT)")
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
    algo = InstitutionalSwingConfluenceAlgo(evaluator.config)

    with open("midcap_tokens.json", 'r') as f:
        symbol_map = json.load(f)

    interval = "FIVE_MINUTE"
    end_dt = datetime.now()
    start_dt = end_dt - timedelta(days=60)
    from_date = start_dt.strftime("%Y-%m-%d %H:%M")
    to_date = end_dt.strftime("%Y-%m-%d %H:%M")

    time.sleep(0.5)
    index_df = client.fetch_historical_data("99926000", interval, from_date, to_date)
    print(f"Loaded {len(index_df)} NIFTY index candles over 60 days.")

    targets_to_test = [
        {"target_pct": 3.0, "stoploss_pct": 2.0, "max_hold_bars": 187}, # ~2.5 to 3 trading days
        {"target_pct": 5.0, "stoploss_pct": 3.0, "max_hold_bars": 250}, # ~3.5 to 4 trading days
        {"target_pct": 2.0, "stoploss_pct": 1.0, "max_hold_bars": 125}  # ~1.5 to 2 trading days
    ]

    for test in targets_to_test:
        target_pct = test["target_pct"]
        stoploss_pct = test["stoploss_pct"]
        max_bars = test["max_hold_bars"]

        signals = []

        for symbol, token in symbol_map.items():
            if symbol in ["NIFTY50", "BANKNIFTY"]:
                continue

            time.sleep(0.3)  # Rate limit safety delay
            df = client.fetch_historical_data(str(token), interval, from_date, to_date)
            if df.empty or len(df) < 150:
                continue

            step = 10
            for idx in range(50, len(df) - max_bars, step):
                sub_df = df.iloc[:idx+1]
                sub_index = index_df.iloc[:min(idx+1, len(index_df))] if index_df is not None and not index_df.empty else None

                candidate = algo.calculate(symbol, str(token), sub_df, index_df=sub_index)
                if candidate and candidate.signal_direction == "BULLISH":
                    if IndexRegime.is_prescreener_passed("BULLISH", sub_index, enable_prescreener=True):
                        outcome = evaluator.evaluate_signal_outcome(
                            df=df,
                            signal_index=idx,
                            direction="BULLISH",
                            target_pct=target_pct,
                            stoploss_pct=stoploss_pct,
                            max_bars=max_bars,
                            use_trailing_sl=True
                        )
                        signals.append(outcome)

        if not signals:
            print(f"\nTarget +{target_pct}% / SL {stoploss_pct}%: No historical signals generated.")
            continue

        sig_df = pd.DataFrame(signals)
        wins = len(sig_df[sig_df['pnl_pct'] >= (target_pct - 0.1)])
        losses = len(sig_df[sig_df['pnl_pct'] <= -stoploss_pct])
        breakevens = len(sig_df[(sig_df['pnl_pct'] > -stoploss_pct) & (sig_df['pnl_pct'] < (target_pct - 0.1))])
        total = len(sig_df)

        win_rate = (wins / total) * 100.0 if total > 0 else 0.0
        loss_rate = (losses / total) * 100.0 if total > 0 else 0.0
        be_rate = (breakevens / total) * 100.0 if total > 0 else 0.0
        avg_pnl = sig_df['pnl_pct'].mean()
        profit_factor = sig_df[sig_df['pnl_pct'] > 0]['pnl_pct'].sum() / (abs(sig_df[sig_df['pnl_pct'] < 0]['pnl_pct'].sum()) + 1e-9)

        print(f"\n==========================================================================================================")
        print(f"  RESULTS FOR TARGET: +{target_pct}% | STOPLOSS: {stoploss_pct}% (60 DAYS REAL MARKET DATA)")
        print(f"==========================================================================================================")
        print(f"Total Signals: {total} | Win Rate: {win_rate:.2f}% | Loss Rate: {loss_rate:.2f}% | Breakeven Rate: {be_rate:.2f}%")
        print(f"Average Return per Trade: {avg_pnl:+.2f}% | Profit Factor: {profit_factor:.2f}")

if __name__ == "__main__":
    run_60day_backtest()
