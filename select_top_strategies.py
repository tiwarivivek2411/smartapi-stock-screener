import pandas as pd
import json
import os

def generate_production_selection_report(top_n: int = 5):
    db_csv = "db/master_dashboard.csv"
    if not os.path.exists(db_csv):
        print("Database not found. Please run paper_trader.py first.")
        return

    df = pd.read_csv(db_csv)
    
    # Filter out entries with zero trades unless equity moved
    df['total_trades'] = df['open_positions_count'] + df['closed_trades_count']
    
    # Sort by Net MTF Profit (₹) descending, then Win Rate %
    ranked_df = df.sort_values(by=['mtf_leveraged_profit_rs', 'win_rate_pct'], ascending=[False, False]).reset_index(drop=True)

    print("\n" + "=" * 130)
    print(f"        🏆 TOP {top_n} PRODUCTION DEPLOYMENT RECOMMENDATIONS (RANKED FOR REAL CASH DEPLOYMENT)")
    print("=" * 130)
    
    header = f"{'Rank':<5} | {'Algorithm Name':<35} | {'Mode':<16} | {'Closed':<6} | {'Win %':<6} | {'TP Hit %':<8} | {'MTF Profit (₹)':<15}"
    print(header)
    print("-" * len(header))

    top_candidates = []
    for idx, row in ranked_df.head(top_n).iterrows():
        rank = idx + 1
        profit_str = f"₹{row['mtf_leveraged_profit_rs']:+,.2f}"
        print(f"{rank:<5} | {row['algo_name']:<35} | {row['mode_key']:<16} | {row['closed_trades_count']:<6} | {row['win_rate_pct']:<6.1f} | {row['tp_achieved_rate_pct']:<8.1f} | {profit_str:<15}")
        top_candidates.append(row)

    print("=" * 130)
    print("\n💡 RECOMMENDED LIVE CASH CAPITAL DEPLOYMENT PLAN:")
    print("-" * 75)
    print(f"If deploying ₹10,00,000 (₹10 Lakhs Total Real Cash Capital):")
    
    if len(top_candidates) >= 2:
        c1 = top_candidates[0]
        c2 = top_candidates[1]
        print(f"  • Strategy 1 (₹5,00,000 Allocation): [{c1['algo_name']}] in Mode [{c1['mode_key']}]")
        print(f"    - ₹1,00,000 per stock across 5 maximum concurrent stocks")
        print(f"    - Historical MTF Profit: ₹{c1['mtf_leveraged_profit_rs']:+,.2f} | Win Rate: {c1['win_rate_pct']}%\n")

        print(f"  • Strategy 2 (₹5,00,000 Allocation): [{c2['algo_name']}] in Mode [{c2['mode_key']}]")
        print(f"    - ₹1,00,000 per stock across 5 maximum concurrent stocks")
        print(f"    - Historical MTF Profit: ₹{c2['mtf_leveraged_profit_rs']:+,.2f} | Win Rate: {c2['win_rate_pct']}%\n")

if __name__ == "__main__":
    generate_production_selection_report(top_n=5)
