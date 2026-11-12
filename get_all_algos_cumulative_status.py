import json
import os
import pandas as pd

def print_all_algo_status():
    dash_file = "db/master_dashboard.csv"
    if not os.path.exists(dash_file):
        print("Master dashboard file not found.")
        return

    df = pd.read_csv(dash_file)
    
    # Aggregate per Algorithm across all 6 modes
    algo_summary = []

    grouped = df.groupby('algo_name')
    for algo_name, group in grouped:
        total_open = group['open_positions_count'].sum()
        total_closed = group['closed_trades_count'].sum()
        
        # Best Mode by Profit
        best_row = group.sort_values(by='mtf_leveraged_profit_rs', ascending=False).iloc[0]
        best_mode = best_row['mode_key']
        best_mode_profit = best_row['mtf_leveraged_profit_rs']
        best_mode_win_rate = best_row['win_rate_pct']
        best_mode_tp_rate = best_row['tp_achieved_rate_pct']

        total_profit_all_modes = group['mtf_leveraged_profit_rs'].sum()

        algo_summary.append({
            "algo_name": algo_name,
            "total_open": total_open,
            "total_closed": total_closed,
            "best_mode": best_mode,
            "best_win_rate_pct": round(best_mode_win_rate, 1),
            "best_tp_rate_pct": round(best_mode_tp_rate, 1),
            "best_mode_profit_rs": round(best_mode_profit, 2),
            "total_profit_all_modes_rs": round(total_profit_all_modes, 2)
        })

    summary_df = pd.DataFrame(algo_summary).sort_values(by='best_mode_profit_rs', ascending=False).reset_index(drop=True)

    pd.set_option('display.max_rows', 100)
    pd.set_option('display.max_columns', 10)
    pd.set_option('display.width', 1000)

    print("\n" + "=" * 140)
    print("          📊 ALL 28 QUANTITATIVE ALGORITHMS CUMULATIVE STATUS LEADERBOARD (RANKED BY BEST MODE PROFIT)")
    print("=" * 140)

    header = f"{'Rank':<5} | {'Algorithm Name':<42} | {'Closed':<7} | {'Best Mode':<15} | {'Win %':<6} | {'TP Hit %':<8} | {'Best Mode Profit (₹)':<20} | {'Total All Modes Profit (₹)':<22}"
    print(header)
    print("-" * len(header))

    for idx, row in summary_df.iterrows():
        rank = idx + 1
        best_profit_str = f"₹{row['best_mode_profit_rs']:+,.2f}"
        total_profit_str = f"₹{row['total_profit_all_modes_rs']:+,.2f}"
        print(f"{rank:<5} | {row['algo_name']:<42} | {row['total_closed']:<7} | {row['best_mode']:<15} | {row['best_win_rate_pct']:<6.1f} | {row['best_tp_rate_pct']:<8.1f} | {best_profit_str:<20} | {total_profit_str:<22}")

    print("=" * 140 + "\n")

    with open("db/all_algo_status_summary.json", 'w') as f:
        json.dump(algo_summary, f, indent=4)

if __name__ == "__main__":
    print_all_algo_status()
