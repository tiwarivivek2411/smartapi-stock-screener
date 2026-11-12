import json
import os
import pandas as pd
import numpy as np

def run_parameter_optimization():
    closed_file = "db/closed_trades_master.json"
    if not os.path.exists(closed_file):
        print("No closed trades database found in db/. Run live screener or backtests first.")
        return

    with open(closed_file, 'r') as f:
        closed_trades = json.load(f)

    if not closed_trades:
        print("Closed trades database is empty.")
        return

    df = pd.DataFrame(closed_trades)
    print("\n==========================================================================================================================================")
    print("      4-DIMENSIONAL PARAMETER OPTIMIZER & PEAK TARGET ANALYSIS (ALGO, MODE, SL%, TP%)")
    print("==========================================================================================================================================")
    print(f"Loaded {len(df)} total closed trade logs from persistent database.\n")

    # Filter Intraday 3PM trades
    intraday_df = df[df['mode_key'] == 'intraday_3pm'].copy()

    if not intraday_df.empty and 'max_pnl_pct_reached' in intraday_df.columns:
        valid_peaks = intraday_df['max_pnl_pct_reached'].dropna()
        if not valid_peaks.empty:
            avg_peak = valid_peaks.mean()
            median_peak = valid_peaks.median()
            p75_peak = np.percentile(valid_peaks, 75)
            p90_peak = np.percentile(valid_peaks, 90)

            print("📊 EMPIRICAL PEAK TARGET (MAX FAVORABLE EXCURSION) DISTRIBUTION FOR INTRADAY:")
            print("-" * 80)
            print(f"  • Average Peak Gain Reached: +{avg_peak:.2f}%")
            print(f"  • Median Peak Gain Reached : +{median_peak:.2f}% (Optimal Base Target)")
            print(f"  • 75th Percentile Peak Gain: +{p75_peak:.2f}% (High Conviction Target)")
            print(f"  • 90th Percentile Peak Gain: +{p90_peak:.2f}% (Maximum Feasible Intraday TP)")
            print("-" * 80 + "\n")

    # Grid Search simulation across TP and SL combinations
    tps_to_test = [1.0, 1.2, 1.5, 1.8, 2.0, 2.5, 3.0]
    sls_to_test = [1.0, 1.5, 2.0, 2.5]

    print("🏆 OPTIMAL PARAMETER GRID SEARCH RESULTS (TOP ALGORITHMS IN INTRADAY MODE):")
    print("-" * 110)
    header = f"{'Algorithm Name':<32} | {'Optimal TP %':<12} | {'Optimal SL %':<12} | {'Simulated Win %':<15} | {'Simulated Profit Factor':<22}"
    print(header)
    print("-" * len(header))

    algo_groups = df.groupby('algo_name')
    for algo_name, group_df in algo_groups:
        best_tp = 3.0
        best_sl = 2.0
        best_win_rate = 0.0
        best_profit_factor = 0.0

        for tp in tps_to_test:
            for sl in sls_to_test:
                sim_wins = 0
                sim_gross_gain = 0.0
                sim_gross_loss = 0.0

                for _, trade in group_df.iterrows():
                    peak = trade.get('max_pnl_pct_reached') or trade.get('pnl_pct_unleveraged') or 0.0
                    actual_pnl = trade.get('pnl_pct_unleveraged') or 0.0

                    if peak >= tp:
                        sim_wins += 1
                        sim_gross_gain += tp
                    elif actual_pnl <= -sl:
                        sim_gross_loss += sl
                    else:
                        if actual_pnl > 0:
                            sim_wins += 1
                            sim_gross_gain += actual_pnl
                        else:
                            sim_gross_loss += abs(actual_pnl)

                total_sim = len(group_df)
                sim_win_rate = (sim_wins / total_sim) * 100.0 if total_sim > 0 else 0.0
                pf = sim_gross_gain / (sim_gross_loss + 1e-9)

                if pf > best_profit_factor or (pf == best_profit_factor and sim_win_rate > best_win_rate):
                    best_profit_factor = pf
                    best_win_rate = sim_win_rate
                    best_tp = tp
                    best_sl = sl

        print(f"{algo_name:<32} | +{best_tp:<11.1f}% | {best_sl:<11.1f}% | {best_win_rate:<15.1f}% | {best_profit_factor:<22.2f}")

    print("=" * 110 + "\n")

if __name__ == "__main__":
    run_parameter_optimization()
