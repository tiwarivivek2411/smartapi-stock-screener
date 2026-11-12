import json
import os
import pandas as pd

def print_final_eod_results():
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

    today_str = "2026-08-24"

    closed_df = pd.DataFrame(closed_trades) if closed_trades else pd.DataFrame()
    open_df = pd.DataFrame(open_positions) if open_positions else pd.DataFrame()

    today_closed = pd.DataFrame()
    if not closed_df.empty and 'exit_timestamp' in closed_df.columns:
        closed_df['exit_date'] = closed_df['exit_timestamp'].astype(str).str.slice(0, 10)
        today_closed = closed_df[closed_df['exit_date'] == today_str]

    today_closed_count = len(today_closed)
    today_pnl = today_closed['mtf_pnl_rs_leveraged'].sum() if today_closed_count > 0 else 0.0
    today_wins = len(today_closed[today_closed['pnl_pct_unleveraged'] > 0]) if today_closed_count > 0 else 0
    today_win_rate = (today_wins / today_closed_count * 100.0) if today_closed_count > 0 else 0.0

    print("==========================================================================================================")
    print("      📊 FINAL END-OF-DAY PERFORMANCE REPORT (MONDAY, AUGUST 24, 2026)")
    print("==========================================================================================================")

    print(f"🗓️  TODAY'S MARKET SESSION SUMMARY (MON AUG 24):")
    print(f"  • Closed Trades Executed Today : {today_closed_count} Trades")
    print(f"  • Today's Winning Trades        : {today_wins} Wins")
    print(f"  • Today's Win Rate %            : {today_win_rate:.1f}%")
    print(f"  • Today's Net Realized MTF PnL  : ₹{today_pnl:+,.2f}\n")

    if today_closed_count > 0:
        print("🏆 TODAY'S EXECUTED CLOSED TRADES LEADERBOARD:")
        print("-" * 90)
        view = today_closed[['symbol', 'algo_name', 'entry_price', 'exit_price', 'pnl_pct_unleveraged', 'mtf_pnl_rs_leveraged']].copy()
        view.columns = ['Stock', 'Algorithm Name', 'Entry (₹)', 'Exit (₹)', 'Return %', 'MTF Profit (₹)']
        print(view.to_string(index=False))
        print("-" * 90 + "\n")

    total_closed_count = len(closed_df) if not closed_df.empty else 0
    total_pnl = closed_df['mtf_pnl_rs_leveraged'].sum() if not closed_df.empty and 'mtf_pnl_rs_leveraged' in closed_df.columns else 0.0
    total_wins = len(closed_df[closed_df['pnl_pct_unleveraged'] > 0]) if not closed_df.empty and 'pnl_pct_unleveraged' in closed_df.columns else 0
    total_win_rate = (total_wins / total_closed_count * 100.0) if total_closed_count > 0 else 0.0

    print(f"🌐 GRAND MASTER PORTFOLIO TOTAL (ALL SESSIONS COMBINED ACROSS 168 ORDERBOOKS):")
    print(f"  • Total Closed Trades       : {total_closed_count} Trades")
    print(f"  • Overall Win Rate %        : {total_win_rate:.1f}%")
    print(f"  • Grand Portfolio MTF PnL  : ₹{total_pnl:+,.2f}")
    print("==========================================================================================================\n")

if __name__ == "__main__":
    print_final_eod_results()
