import json
import os
import pandas as pd
import numpy as np

def run_stock_algo_correlation_analysis():
    closed_file = "db/closed_trades_master.json"
    open_file = "db/open_positions_master.json"

    trades = []
    if os.path.exists(closed_file):
        with open(closed_file, 'r') as f:
            trades.extend(json.load(f))
    if os.path.exists(open_file):
        with open(open_file, 'r') as f:
            trades.extend(json.load(f))

    if not trades:
        print("No trade data found in db/. Run live screener or backtests first.")
        return

    df = pd.DataFrame(trades)
    print("\n==========================================================================================================================================")
    print("      STOCK / ETF TO ALGORITHM AFFINITY & CORRELATION ANALYSIS (OPTIMIZING PAIRINGS FOR MAXIMUM ACCURACY)")
    print("==========================================================================================================================================")
    print(f"Analyzing {len(df)} total position records across Stocks and Index ETFs...\n")

    # Group by Stock/ETF Symbol and Algorithm Name
    grouped = df.groupby(['symbol', 'algo_name'])
    
    correlation_records = []
    for (symbol, algo_name), group in grouped:
        total_trades = len(group)
        closed_trades = group[group['status'] == 'CLOSED']
        total_closed = len(closed_trades)

        wins = len(closed_trades[closed_trades['pnl_pct_unleveraged'] > 0]) if total_closed > 0 else 0
        win_rate = round((wins / total_closed) * 100.0, 2) if total_closed > 0 else 0.0

        net_mtf_pnl = closed_trades['mtf_pnl_rs_leveraged'].sum() if total_closed > 0 else 0.0

        correlation_records.append({
            "symbol": symbol,
            "algo_name": algo_name,
            "total_trades": total_trades,
            "total_closed": total_closed,
            "win_rate_pct": win_rate,
            "net_mtf_pnl_rs": round(net_mtf_pnl, 2)
        })

    corr_df = pd.DataFrame(correlation_records)
    sorted_corr = corr_df.sort_values(by=['net_mtf_pnl_rs', 'win_rate_pct'], ascending=[False, False]).reset_index(drop=True)

    print("🏆 TOP HIGH-AFFINITY STOCK / ETF TO ALGORITHM PAIRINGS (RANKED BY REALIZED NET PROFIT):")
    print("-" * 115)
    header = f"{'Rank':<5} | {'Stock / ETF':<12} | {'Algorithm Name':<38} | {'Trades':<8} | {'Win %':<6} | {'Net MTF Profit (₹)':<15}"
    print(header)
    print("-" * len(header))

    for idx, row in sorted_corr.head(15).iterrows():
        rank = idx + 1
        profit_str = f"₹{row['net_mtf_pnl_rs']:+,.2f}"
        print(f"{rank:<5} | {row['symbol']:<12} | {row['algo_name']:<38} | {row['total_trades']:<8} | {row['win_rate_pct']:<6.1f} | {profit_str:<15}")

    print("=" * 115 + "\n")

    print("💡 INSTITUTIONAL STOCK & ETF AFFINITY RULES TO MAXIMIZE ACCURACY:")
    print("-" * 85)
    print("  • Index ETFs (NIFTYBEES, BANKBEES, ITBEES, JUNIORBEES):")
    print("    - Best Paired With: VWAP Reversion, Supertrend & VWAP, Keltner VWAP Dual.")
    print("    - Why: Index ETFs exhibit mean-reverting properties with lower tail risk.\n")

    print("  • High-Beta Momentum Stocks (DIXON, HAL, POLYCAB, KEI):")
    print("    - Best Paired With: Institutional Swing Confluence, Relative Strength, Volatility Squeeze.")
    print("    - Why: High ADR% (>3.5%) stocks deliver explosive multi-day trend expansion.\n")

    print("  • Volatile Midcaps & PSUs (BHEL, PFC, REC, NATIONALUM):")
    print("    - Best Paired With: Liquidity Sweep Reversal, Fail-to-Return Liquidity Trap.")
    print("    - Why: Institutional stop-hunting is common in midcap PSUs before major trend legs.\n")

if __name__ == "__main__":
    run_stock_algo_correlation_analysis()
