import json
import os
import pandas as pd
from datetime import datetime

def print_live_paper_daily_returns():
    print("==========================================================================================================")
    print("      📊 LIVE PAPER TRADING LEADERBOARD (EXCLUSIVE LIVE DATA ONLY | DAILY % RETURN CALCULATOR)")
    print("==========================================================================================================")

    dash_file = "db/master_dashboard.csv"
    if not os.path.exists(dash_file):
        print("Master dashboard file not found.")
        return

    df = pd.read_csv(dash_file)

    # Active live testing days per algorithm
    # Baseline algos started Aug 20 (7 trading days)
    # Algos #27 and #28 added Aug 24 (5 trading days)
    new_algos = ["supertrend_vwap_short", "intraday_gap_down_continuation"]

    records = []
    capital = 500000.0  # ₹5,00,000 per orderbook

    for idx, row in df.iterrows():
        algo_name = row['algo_name']
        mode_key = row['mode_key']
        pnl = row['mtf_leveraged_profit_rs']
        closed_trades = row['closed_trades_count']
        win_rate = row['win_rate_pct']
        tp_rate = row['tp_achieved_rate_pct']

        # Determine active live days
        active_days = 5 if any(k in str(algo_name).lower() for k in ["supertrend & vwap bearish", "gap-down & go"]) else 7

        # Total Return % on ₹5 Lakhs Margin
        total_return_pct = (pnl / capital) * 100.0

        # Daily Rate of Return %
        daily_return_pct = total_return_pct / active_days

        records.append({
            "algo_name": algo_name,
            "mode_key": mode_key,
            "closed_trades": closed_trades,
            "win_rate_pct": win_rate,
            "tp_rate_pct": tp_rate,
            "pnl_rs": round(pnl, 2),
            "active_days": active_days,
            "total_return_pct": round(total_return_pct, 2),
            "daily_return_pct": round(daily_return_pct, 4)
        })

    res_df = pd.DataFrame(records)

    # Sort strictly by positive live realized PnL & Daily Return %
    top_live = res_df.sort_values(by=['pnl_rs', 'daily_return_pct'], ascending=[False, False]).head(15).reset_index(drop=True)

    pd.set_option('display.max_rows', 50)
    pd.set_option('display.max_columns', 10)
    pd.set_option('display.width', 1000)

    header = f"{'Rank':<5} | {'Algorithm Name':<38} | {'Mode Key':<14} | {'Closed':<6} | {'Win %':<6} | {'Live PnL (₹)':<14} | {'Active Days':<11} | {'Total Return %':<15} | {'Daily Return %':<14}"
    print(header)
    print("-" * len(header))

    for idx, row in top_live.iterrows():
        rank = idx + 1
        pnl_str = f"₹{row['pnl_rs']:+,.2f}"
        tot_ret_str = f"{row['total_return_pct']:+.2f}%"
        daily_ret_str = f"{row['daily_return_pct']:+.4f}%/day"
        print(f"{rank:<5} | {row['algo_name']:<38} | {row['mode_key']:<14} | {row['closed_trades']:<6} | {row['win_rate_pct']:<6.1f} | {pnl_str:<14} | {row['active_days']:<11} | {tot_ret_str:<15} | {daily_ret_str:<14}")

    print("=" * 140 + "\n")

    with open("db/live_paper_daily_returns_summary.json", 'w') as f:
        json.dump(records, f, indent=4)

if __name__ == "__main__":
    print_live_paper_daily_returns()
