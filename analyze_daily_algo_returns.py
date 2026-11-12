import json
import os
import pandas as pd
import numpy as np

def run_daily_algo_analysis():
    print("==========================================================================================================")
    print("      🔍 DAY-BY-DAY ALGORITHM PERFORMANCE & DIAGNOSTIC DOWNTURN ANALYZER")
    print("==========================================================================================================")

    closed_file = "db/closed_trades_master.json"
    if not os.path.exists(closed_file):
        print("Closed trades master not found.")
        return

    with open(closed_file, 'r') as f:
        closed_trades = json.load(f)

    if not closed_trades:
        print("No closed trades found.")
        return

    df = pd.DataFrame(closed_trades)
    
    date_col = None
    for col in ['exit_time', 'exit_timestamp', 'entry_time', 'timestamp']:
        if col in df.columns:
            date_col = col
            break

    if not date_col:
        print(f"No date column found. Available columns: {list(df.columns)}")
        return

    df['exit_date'] = df[date_col].astype(str).str.slice(0, 10)

    # 1. Day-by-day PnL breakdown across all trades
    daily_summary = []

    grouped = df.groupby('exit_date')
    cumulative_pnl = 0.0

    for exit_date, group in grouped:
        total_trades = len(group)
        wins = len(group[group['pnl_pct_unleveraged'] > 0])
        win_rate = (wins / total_trades * 100.0) if total_trades > 0 else 0.0
        day_pnl = group['mtf_pnl_rs_leveraged'].sum()
        cumulative_pnl += day_pnl

        # Breakdown by mode type (intraday_3pm vs multi-day swing modes)
        intraday_group = group[group['mode_key'] == 'intraday_3pm']
        intraday_pnl = intraday_group['mtf_pnl_rs_leveraged'].sum() if not intraday_group.empty else 0.0
        
        swing_group = group[group['mode_key'] != 'intraday_3pm']
        swing_pnl = swing_group['mtf_pnl_rs_leveraged'].sum() if not swing_group.empty else 0.0

        daily_summary.append({
            "exit_date": exit_date,
            "total_trades": total_trades,
            "wins": wins,
            "win_rate_pct": round(win_rate, 1),
            "day_pnl_rs": round(day_pnl, 2),
            "intraday_3pm_pnl_rs": round(intraday_pnl, 2),
            "swing_modes_pnl_rs": round(swing_pnl, 2),
            "cumulative_pnl_rs": round(cumulative_pnl, 2)
        })

    daily_df = pd.DataFrame(daily_summary)

    pd.set_option('display.max_rows', 100)
    pd.set_option('display.max_columns', 10)
    pd.set_option('display.width', 1000)

    print("🗓️  EXACT DAY-BY-DAY PERFORMANCE TIMELINE:")
    print("-" * 125)
    header = f"{'Date':<12} | {'Trades':<8} | {'Win %':<6} | {'Day PnL (₹)':<16} | {'Intraday 3pm PnL (₹)':<22} | {'Swing Modes PnL (₹)':<20} | {'Cumulative PnL (₹)':<20}"
    print(header)
    print("-" * len(header))

    for idx, row in daily_df.iterrows():
        day_pnl_str = f"₹{row['day_pnl_rs']:+,.2f}"
        intra_str = f"₹{row['intraday_3pm_pnl_rs']:+,.2f}"
        swing_str = f"₹{row['swing_modes_pnl_rs']:+,.2f}"
        cum_str = f"₹{row['cumulative_pnl_rs']:+,.2f}"
        print(f"{row['exit_date']:<12} | {row['total_trades']:<8} | {row['win_rate_pct']:<6.1f} | {day_pnl_str:<16} | {intra_str:<22} | {swing_str:<20} | {cum_str:<20}")

    print("=" * 125 + "\n")

    # 2. Detailed Algorithm Breakdown per Date for top Algos
    top_algos = ["RSI Range Shift Momentum Breakout", "Keltner Channel & VWAP Dual (Long/Short)", "Multi-Timeframe EMA Ribbon Alignment", "Fail-to-Return / Liquidity Trap Reversal"]
    print("🔬 ALGORITHM-SPECIFIC DAY-BY-DAY PN L BREAKDOWN FOR TOP STRATEGIES:")
    print("-" * 125)

    sub_df = df[df['algo_name'].isin(top_algos)]
    algo_date_pivot = sub_df.pivot_table(index='exit_date', columns='algo_name', values='mtf_pnl_rs_leveraged', aggfunc='sum').fillna(0.0)
    print(algo_date_pivot.to_string())
    print("-" * 125 + "\n")

if __name__ == "__main__":
    run_daily_algo_analysis()
