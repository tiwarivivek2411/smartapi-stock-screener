import json
import os
import pandas as pd
from datetime import datetime

def calculate_today_vs_total_pnl():
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

    today_str = datetime.now().strftime("%Y-%m-%d")

    # Filter closed trades closed today
    closed_df = pd.DataFrame(closed_trades) if closed_trades else pd.DataFrame()
    open_df = pd.DataFrame(open_positions) if open_positions else pd.DataFrame()

    today_closed_pnl = 0.0
    today_closed_count = 0
    today_wins = 0

    if not closed_df.empty and 'exit_timestamp' in closed_df.columns:
        closed_df['exit_date'] = closed_df['exit_timestamp'].astype(str).str.slice(0, 10)
        today_closed = closed_df[closed_df['exit_date'] == today_str]
        today_closed_count = len(today_closed)
        if today_closed_count > 0:
            today_closed_pnl = today_closed['mtf_pnl_rs_leveraged'].sum()
            today_wins = len(today_closed[today_closed['pnl_pct_unleveraged'] > 0])

    today_open_pnl = 0.0
    today_open_count = 0
    if not open_df.empty and 'entry_timestamp' in open_df.columns:
        open_df['entry_date'] = open_df['entry_timestamp'].astype(str).str.slice(0, 10)
        today_open = open_df[open_df['entry_date'] == today_str]
        today_open_count = len(today_open)

    # Total Cumulative PnL across all time
    total_closed_pnl = closed_df['mtf_pnl_rs_leveraged'].sum() if not closed_df.empty and 'mtf_pnl_rs_leveraged' in closed_df.columns else 0.0
    total_closed_count = len(closed_df) if not closed_df.empty else 0
    total_wins = len(closed_df[closed_df['pnl_pct_unleveraged'] > 0]) if not closed_df.empty and 'pnl_pct_unleveraged' in closed_df.columns else 0

    print("==========================================================================================================")
    print("      📊 LIVE PERFORMANCE BREAKDOWN: TODAY'S P&L (MON AUG 24) vs TOTAL CUMULATIVE P&L")
    print("==========================================================================================================")

    today_win_rate = (today_wins / today_closed_count * 100.0) if today_closed_count > 0 else 0.0
    total_win_rate = (total_wins / total_closed_count * 100.0) if total_closed_count > 0 else 0.0

    print(f"🗓️  TODAY'S PERFORMANCE (MONDAY, AUGUST 24, 2026):")
    print(f"  • Closed Trades Today       : {today_closed_count} Trades")
    print(f"  • Active Open Positions     : {today_open_count} Positions")
    print(f"  • Today's Win Rate %        : {today_win_rate:.1f}%")
    print(f"  • Today's Realized MTF Profit: ₹{today_closed_pnl:+,.2f}\n")

    print(f"🌐 TOTAL CUMULATIVE PERFORMANCE (ALL SESSIONS COMBINED):")
    print(f"  • Total Closed Trades       : {total_closed_count} Trades")
    print(f"  • Cumulative Win Rate %     : {total_win_rate:.1f}%")
    print(f"  • Total Realized MTF Profit : ₹{total_closed_pnl:+,.2f}")
    print("==========================================================================================================\n")

if __name__ == "__main__":
    calculate_today_vs_total_pnl()
