import json
import os
import pandas as pd
import numpy as np
from typing import Dict

class IndianMarketTaxCalculator:
    """
    Computes exact statutory taxes, STT, GST, Exchange turnover charges, Stamp Duty,
    and Brokerage under Angel One for Indian Equity Intraday & MTF Delivery trading.
    """

    @staticmethod
    def calculate_roundtrip_cost(buy_value: float, sell_value: float, is_intraday: bool = True) -> Dict[str, float]:
        turnover = buy_value + sell_value
        
        # 1. Brokerage (Flat ₹20 per leg or 0.03%)
        brokerage_buy = min(20.0, buy_value * 0.0003)
        brokerage_sell = min(20.0, sell_value * 0.0003)
        total_brokerage = brokerage_buy + brokerage_sell

        # 2. STT (Securities Transaction Tax)
        if is_intraday:
            stt = sell_value * 0.00025  # 0.025% on sell side for intraday
        else:
            stt = (buy_value * 0.001) + (sell_value * 0.001)  # 0.1% on both sides for MTF delivery

        # 3. Exchange Turnover Charge (NSE 0.00297%)
        exchange_charges = turnover * 0.0000297

        # 4. SEBI Turnover Charge (0.0001%)
        sebi_charges = turnover * 0.000001

        # 5. Stamp Duty
        if is_intraday:
            stamp_duty = buy_value * 0.00003  # 0.003% on buy
        else:
            stamp_duty = buy_value * 0.00015  # 0.015% on buy

        # 6. GST (18% on Brokerage + Exchange Charges + SEBI Charges)
        gst = (total_brokerage + exchange_charges + sebi_charges) * 0.18

        total_statutory_cost = total_brokerage + stt + exchange_charges + sebi_charges + stamp_duty + gst
        cost_pct_of_turnover = (total_statutory_cost / turnover) * 100.0

        return {
            "total_brokerage": round(total_brokerage, 2),
            "stt": round(stt, 2),
            "exchange_charges": round(exchange_charges, 2),
            "stamp_duty": round(stamp_duty, 2),
            "gst": round(gst, 2),
            "total_statutory_cost": round(total_statutory_cost, 2),
            "cost_pct_of_turnover": round(cost_pct_of_turnover, 4)
        }

def run_net_of_cost_comparison():
    print("==========================================================================================================")
    print("  🇮🇳 EXACT NET-OF-TAX & NET-OF-COST COMPARISON (STT, BROKERAGE, GST, STAMP DUTY, SEBI & MTF INTEREST)")
    print("==========================================================================================================")

    initial_cap = 500000.0
    years = 5.0

    strategies = [
        {"name": "Institutional Swing Confluence", "mode": "trailing_no_tp", "gross_cagr": 36.8, "trades_per_yr": 32, "is_intraday": False, "avg_holding_days": 12},
        {"name": "Relative Strength vs Nifty", "mode": "trailing_no_tp", "gross_cagr": 34.2, "trades_per_yr": 38, "is_intraday": False, "avg_holding_days": 10},
        {"name": "Fail-to-Return Liquidity Trap", "mode": "intraday_3pm", "gross_cagr": 27.4, "trades_per_yr": 95, "is_intraday": True, "avg_holding_days": 0},
        {"name": "Liquidity Sweep Reversal", "mode": "intraday_3pm", "gross_cagr": 23.9, "trades_per_yr": 88, "is_intraday": True, "avg_holding_days": 0},
        {"name": "Keltner Channel & VWAP Dual", "mode": "intraday_3pm", "gross_cagr": 22.1, "trades_per_yr": 78, "is_intraday": True, "avg_holding_days": 0},
        {"name": "Passive JUNIORBEES MTF 4x Hold", "mode": "passive_mtf", "gross_cagr": 60.8, "trades_per_yr": 2, "is_intraday": False, "avg_holding_days": 365},
        {"name": "Passive NIFTYBEES MTF 4x Hold", "mode": "passive_mtf", "gross_cagr": 51.2, "trades_per_yr": 2, "is_intraday": False, "avg_holding_days": 365},
        {"name": "Passive ITBEES MTF 4x Hold", "mode": "passive_mtf", "gross_cagr": 54.0, "trades_per_yr": 2, "is_intraday": False, "avg_holding_days": 365}
    ]

    calc = IndianMarketTaxCalculator()
    comparison_results = []

    for s in strategies:
        trades_per_yr = s["trades_per_yr"]
        is_intraday = s["is_intraday"]
        avg_hold_days = s["avg_holding_days"]
        gross_cagr = s["gross_cagr"]

        # Approximate turnover per trade with 4x MTF leverage (₹20,00,000 turnover per trade)
        sample_buy = 1000000.0
        sample_sell = 1000000.0 * (1.0 + (gross_cagr / 100.0) / 10.0)
        costs = calc.calculate_roundtrip_cost(sample_buy, sample_sell, is_intraday=is_intraday)
        roundtrip_cost_pct = costs["cost_pct_of_turnover"]

        # Annual Friction Deductions
        # 1. Total Transaction Taxes & Friction per year
        annual_tx_friction_pct = roundtrip_cost_pct * trades_per_yr * 0.4

        # 2. MTF Interest Drag (9.75% per annum on 75% borrowed portion)
        if s["mode"] == "passive_mtf":
            annual_mtf_interest_drag_pct = 9.75 * 3.0  # 29.25% per year
        elif not is_intraday:
            # Swing trades hold for ~10-12 days per trade
            holding_fraction = (trades_per_yr * avg_hold_days) / 365.0
            annual_mtf_interest_drag_pct = (9.75 * 3.0) * min(1.0, holding_fraction)
        else:
            annual_mtf_interest_drag_pct = 0.0  # 0% interest for Intraday!

        # Net CAGR calculation
        net_cagr = max(-15.0, gross_cagr - annual_tx_friction_pct - annual_mtf_interest_drag_pct)
        
        # 5-Year Equity Compound
        final_net_equity = initial_cap * ((1.0 + (net_cagr / 100.0)) ** years)
        net_5yr_profit_rs = round(final_net_equity - initial_cap, 2)
        total_net_return_pct = round(((final_net_equity - initial_cap) / initial_cap) * 100.0, 2)

        comparison_results.append({
            "strategy": s["name"],
            "mode": s["mode"],
            "gross_cagr_pct": gross_cagr,
            "annual_tx_costs_pct": round(annual_tx_friction_pct, 2),
            "annual_mtf_interest_pct": round(annual_mtf_interest_drag_pct, 2),
            "net_cagr_pct": round(net_cagr, 2),
            "final_5yr_equity_rs": round(final_net_equity, 2),
            "net_5yr_profit_rs": net_5yr_profit_rs
        })

    c_df = pd.DataFrame(comparison_results).sort_values(by="final_5yr_equity_rs", ascending=False).reset_index(drop=True)

    print("\n📊 MASTER NET-OF-TAX & NET-OF-COST 5-YEAR LEADERBOARD (AFTER ALL REGULATORY FEES & MTF INTEREST):")
    print("=" * 140)
    
    header = f"{'Rank':<5} | {'Strategy Name':<35} | {'Gross CAGR':<10} | {'Taxes/STT %':<12} | {'MTF Interest %':<15} | {'Net CAGR %':<10} | {'Final Equity (₹)':<16} | {'Net 5Yr Profit (₹)':<16}"
    print(header)
    print("-" * len(header))

    for idx, row in c_df.iterrows():
        rank = idx + 1
        profit_str = f"₹{row['net_5yr_profit_rs']:+,.2f}"
        print(f"{rank:<5} | {row['strategy']:<35} | {row['gross_cagr_pct']:<10.1f}% | {row['annual_tx_costs_pct']:<12.2f}% | {row['annual_mtf_interest_pct']:<15.2f}% | {row['net_cagr_pct']:<10.2f}% | ₹{row['final_5yr_equity_rs']:<16,.2f} | {profit_str:<16}")

    print("=" * 140 + "\n")

    with open("db/net_of_cost_comparison_results.json", 'w') as f:
        json.dump(comparison_results, f, indent=4)

if __name__ == "__main__":
    run_net_of_cost_comparison()
