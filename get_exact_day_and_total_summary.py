import json
import os
import pandas as pd

def print_exact_day_vs_total_summary():
    closed_file = "db/closed_trades_master.json"
    open_file = "db/open_positions_master.json"

    closed_trades = []
    open_positions = []

    if os.path.exists(closed_file):
        with open(closed_file, 'r') as f:
            closed_trades = json.load(f)

    if os.path.exists(open_file):
        with open(open_file, 'r') as f:
            open_positions = json.load(f)

    closed_df = pd.DataFrame(closed_trades) if closed_trades else pd.DataFrame()
    open_df = pd.DataFrame(open_positions) if open_positions else pd.DataFrame()

    latest_date_str = "2026-08-28"  # Friday Aug 28 trading session

    today_closed = pd.DataFrame()
    if not closed_df.empty and 'exit_timestamp' in closed_df.columns:
        closed_df['exit_date'] = closed_df['exit_timestamp'].astype(str).str.slice(0, 10)
        today_closed = closed_df[closed_df['exit_date'] == latest_date_str]

    today_closed_count = len(today_closed)
    today_pnl = today_closed['mtf_pnl_rs_leveraged'].sum() if today_closed_count > 0 else 0.0
    today_wins = len(today_closed[today_closed['pnl_pct_unleveraged'] > 0]) if today_closed_count > 0 else 0
    today_win_rate = (today_wins / today_closed_count * 100.0) if today_closed_count > 0 else 0.0

    total_closed_count = len(closed_df) if not closed_df.empty else 0
    total_pnl = closed_df['mtf_pnl_rs_leveraged'].sum() if not closed_df.empty and 'mtf_pnl_rs_leveraged' in closed_df.columns else 0.0
    total_wins = len(closed_df[closed_df['pnl_pct_unleveraged'] > 0]) if not closed_df.empty and 'pnl_pct_unleveraged' in closed_df.columns else 0
    total_win_rate = (total_wins / total_closed_count * 100.0) if total_closed_count > 0 else 0.0

    print("\n" + "=" * 100)
    print("      📊 EXACT ALGORITHM RESULTS SUMMARY: LATEST DAY SESSION vs TOTAL CUMULATIVE")
    print("=" * 100)

    print(f"🗓️  LATEST TRADING DAY SESSION (FRIDAY, AUGUST 28, 2026):")
    print(f"  • Closed Trades Executed Today : {today_closed_count} Trades")
    print(f"  • Winning Trades Today          : {today_wins} Wins")
    print(f"  • Today's Win Rate %            : {today_win_rate:.1f}%")
    print(f"  • Today's Realized MTF Net PnL  : ₹{today_pnl:+,.2f}\n")

    print(f"🌐 TOTAL CUMULATIVE ALL-TIME PERFORMANCE (ALL 168 ORDERBOOKS COMBINED):")
    print(f"  • Total Closed Trades Executed : {total_closed_count} Trades")
    print(f"  • Overall Cumulative Win Rate % : {total_win_rate:.1f}%")
    print(f"  • Grand Portfolio MTF Net PnL  : ₹{total_pnl:+,.2f}")
    print("=" * 100 + "\n")

    if today_closed_count > 0:
        print("🏆 TRADES EXECUTED DURING LATEST DAY SESSION:")
        print("-" * 100)
        view = today_closed[['symbol', 'algo_name', 'mode_key', 'entry_price', 'exit_price', 'pnl_pct_unleveraged', 'mtf_pnl_rs_leveraged']].copy()
        view.columns = ['Stock', 'Algorithm Name', 'Mode', 'Entry (₹)', 'Exit (₹)', 'Return %', 'MTF Profit (₹)']
        print(view.to_string(index=False))
        print("-" * 100 + "\n")

if __name__ == "__main__":
    print_exact_day_vs_total_summary()
