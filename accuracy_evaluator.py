import os
import json
import argparse
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict
from smart_api_client import SmartAPIClient
from algorithms import ALGORITHM_REGISTRY, Candidate

class AccuracyEvaluator:
    def __init__(self, api_client: SmartAPIClient = None, config_path: str = "config.json"):
        self.api_client = api_client
        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self) -> dict:
        default_config = {
            "symbol_file": "nifty50_tokens.json",
            "interval": "FIVE_MINUTE",
            "lookback_days": 20,
            "min_potential_move_pct": 3.0,
            "target_profit_pct": 3.0,
            "stoploss_pcts": [1.0, 1.5, 2.0, 2.5, 3.0],
            "max_hold_bars": 187  # ~2.5 trading days (187 five-minute bars)
        }
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    data = json.load(f)
                    screener_cfg = data.get("screener", data)
                    default_config.update(screener_cfg)
            except Exception:
                pass
        return default_config

    def generate_synthetic_candles(self, symbol: str, num_days: int = 20, volatility: float = 0.008) -> pd.DataFrame:
        """
        Generates realistic multi-day 5-minute candle data with realistic intraday trends,
        volume spikes, and volatility clusters.
        """
        records = []
        base_price = 500.0 if symbol != "NIFTY50" else 22000.0
        price = base_price
        start_dt = datetime.now() - timedelta(days=num_days)

        for day in range(num_days):
            day_time = start_dt + timedelta(days=day)
            if day_time.weekday() >= 5:
                continue

            bar_time = day_time.replace(hour=9, minute=15, second=0, microsecond=0)
            daily_trend = np.random.choice([0.0003, -0.0003, 0.0001, 0.0005, -0.0004])

            for bar in range(75):
                ret = np.random.normal(daily_trend, volatility)
                open_p = price
                close_p = price * (1.0 + ret)
                high_p = max(open_p, close_p) * (1.0 + abs(np.random.normal(0, volatility * 0.4)))
                low_p = min(open_p, close_p) * (1.0 - abs(np.random.normal(0, volatility * 0.4)))
                vol = np.random.randint(5000, 50000)
                if bar in [0, 1, 73, 74] or abs(ret) > volatility * 1.5:
                    vol *= np.random.randint(2, 5)

                records.append({
                    "timestamp": bar_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "open": round(open_p, 2),
                    "high": round(high_p, 2),
                    "low": round(low_p, 2),
                    "close": round(close_p, 2),
                    "volume": int(vol)
                })
                price = close_p
                bar_time += timedelta(minutes=5)

        return pd.DataFrame(records)

    def evaluate_signal_outcome(self, df: pd.DataFrame, signal_index: int, direction: str, target_pct: float, stoploss_pct: float, max_bars: int = 187, use_trailing_sl: bool = True, auto_squareoff_3pm: bool = False) -> dict:
        entry_price = float(df['close'].iloc[signal_index])
        if entry_price <= 0:
            return {"outcome": "INVALID", "pnl_pct": 0.0, "bars_held": 0}

        future_df = df.iloc[signal_index + 1 : signal_index + 1 + max_bars]
        if future_df.empty:
            return {"outcome": "INSUFFICIENT_DATA", "pnl_pct": 0.0, "bars_held": 0}

        entry_timestamp = pd.to_datetime(df['timestamp'].iloc[signal_index])

        if direction == "BULLISH":
            has_target = target_pct < 900.0
            target_price = entry_price * (1.0 + (target_pct / 100.0)) if has_target else 999999.0
            stop_price = entry_price * (1.0 - (stoploss_pct / 100.0))
            highest_price = entry_price

            for bar_idx, (_, row) in enumerate(future_df.iterrows(), start=1):
                high_p = float(row['high'])
                low_p = float(row['low'])
                close_p = float(row['close'])
                highest_price = max(highest_price, high_p)
                bar_time = pd.to_datetime(row['timestamp'])

                # Trailing SL: if price moves +1.0% up, trail stop to breakeven
                if use_trailing_sl and (highest_price - entry_price) / entry_price >= 0.01:
                    stop_price = max(stop_price, entry_price)

                # Intraday 3:00 PM Squareoff check
                if auto_squareoff_3pm and bar_time.date() == entry_timestamp.date() and bar_time.hour >= 15:
                    exit_pnl = ((close_p - entry_price) / entry_price) * 100.0
                    return {"outcome": "WIN" if exit_pnl > 0 else ("LOSS" if exit_pnl < 0 else "BREAKEVEN"), "pnl_pct": round(exit_pnl, 2), "bars_held": bar_idx}

                if low_p <= stop_price:
                    exit_pnl = ((stop_price - entry_price) / entry_price) * 100.0
                    return {"outcome": "LOSS" if exit_pnl < 0 else "BREAKEVEN", "pnl_pct": round(exit_pnl, 2), "bars_held": bar_idx}

                if has_target and high_p >= target_price:
                    return {"outcome": "WIN", "pnl_pct": target_pct, "bars_held": bar_idx}

            final_price = float(future_df['close'].iloc[-1])
            final_pnl = ((final_price - entry_price) / entry_price) * 100.0
            return {"outcome": "TIMEOUT", "pnl_pct": round(final_pnl, 2), "bars_held": len(future_df)}

        elif direction == "BEARISH":
            target_price = entry_price * (1.0 - (target_pct / 100.0))
            stop_price = entry_price * (1.0 + (stoploss_pct / 100.0))
            lowest_price = entry_price

            for bar_idx, (_, row) in enumerate(future_df.iterrows(), start=1):
                high_p = float(row['high'])
                low_p = float(row['low'])
                lowest_price = min(lowest_price, low_p)

                if use_trailing_sl and (entry_price - lowest_price) / entry_price >= 0.01:
                    stop_price = min(stop_price, entry_price)

                if high_p >= stop_price:
                    exit_pnl = ((entry_price - stop_price) / entry_price) * 100.0
                    return {"outcome": "LOSS" if exit_pnl < 0 else "BREAKEVEN", "pnl_pct": round(exit_pnl, 2), "bars_held": bar_idx}

                if low_p <= target_price:
                    return {"outcome": "WIN", "pnl_pct": target_pct, "bars_held": bar_idx}

            final_price = float(future_df['close'].iloc[-1])
            final_pnl = ((entry_price - final_price) / entry_price) * 100.0
            return {"outcome": "TIMEOUT", "pnl_pct": round(final_pnl, 2), "bars_held": len(future_df)}

        return {"outcome": "INVALID", "pnl_pct": 0.0, "bars_held": 0}

    def run_backtest(self, stoploss_pcts: List[float] = [2.0, 3.0], target_pct: float = 5.0, lookback_days: int = 60, use_synthetic: bool = False, use_trailing_sl: bool = True, use_prescreener: bool = True) -> pd.DataFrame:
        symbol_file = self.config.get("symbol_file", "midcap_tokens.json")
        symbol_map = {}
        if os.path.exists(symbol_file):
            with open(symbol_file, 'r') as f:
                symbol_map = json.load(f)
        else:
            symbol_map = {"RELIANCE": "2885", "SBIN": "3045", "INFY": "1594", "TCS": "11536", "HDFCBANK": "1333"}

        interval = self.config.get("interval", "FIVE_MINUTE")
        end_dt = datetime.now()
        start_dt = end_dt - timedelta(days=lookback_days)
        from_date = start_dt.strftime("%Y-%m-%d %H:%M")
        to_date = end_dt.strftime("%Y-%m-%d %H:%M")

        data_source = "SYNTHETIC MARKET CANDLES" if use_synthetic or not self.api_client else "LIVE SMARTAPI DATA"
        prescreener_status = "ENABLED (Sector & Index Filter ON)" if use_prescreener else "DISABLED (Raw Screener)"

        print(f"\n====================================================================================================")
        print(f"   HISTORICAL ACCURACY BACKTEST ({lookback_days} DAYS REAL MARKET DATA | PRESCREENER: {prescreener_status})")
        print(f"====================================================================================================")
        print(f"Target Profit: +{target_pct}% | Stop-losses Tested: {stoploss_pcts}% | Trailing SL: {use_trailing_sl}\n")

        index_df = None
        if use_synthetic or not self.api_client:
            index_df = self.generate_synthetic_candles("NIFTY50", num_days=lookback_days, volatility=0.005)
        else:
            index_df = self.api_client.fetch_historical_data("99926000", interval, from_date, to_date)

        signals = []
        instantiated_algos = {key: cls(self.config) for key, cls in ALGORITHM_REGISTRY.items()}

        for symbol, token in symbol_map.items():
            if symbol in ["NIFTY50", "BANKNIFTY"]:
                continue

            if use_synthetic or not self.api_client:
                df = self.generate_synthetic_candles(symbol, num_days=lookback_days, volatility=np.random.uniform(0.007, 0.014))
            else:
                df = self.api_client.fetch_historical_data(str(token), interval, from_date, to_date)

            if df.empty or len(df) < 150:
                continue

            step = 10
            for idx in range(50, len(df) - self.config.get("max_hold_bars", 187), step):
                sub_df = df.iloc[:idx+1]
                sub_index = index_df.iloc[:min(idx+1, len(index_df))] if index_df is not None and not index_df.empty else None

                for algo_key, algo in instantiated_algos.items():
                    candidate = algo.calculate(symbol, str(token), sub_df, index_df=sub_index)
                    if candidate and candidate.signal_direction == "BULLISH":
                        # Apply Top-Down Sector & Index Prescreener Filter if enabled
                        from index_regime import IndexRegime
                        if IndexRegime.is_prescreener_passed("BULLISH", sub_index, enable_prescreener=use_prescreener):
                            signals.append({
                                "symbol": symbol,
                                "token": token,
                                "signal_index": idx,
                                "timestamp": df['timestamp'].iloc[idx],
                                "algo_key": algo_key,
                                "algo_name": algo.name,
                                "direction": candidate.signal_direction,
                                "entry_price": candidate.latest_price,
                                "full_df": df
                            })

        if not signals:
            print("No signals generated during evaluation window.")
            return pd.DataFrame()

        print(f"Generated {len(signals)} total historical signals over {lookback_days} days. Running outcome simulations...\n")

        results = []
        for sl in stoploss_pcts:
            for algo_key in ALGORITHM_REGISTRY.keys():
                algo_signals = [s for s in signals if s['algo_key'] == algo_key]
                wins, losses, breakevens, timeouts = 0, 0, 0, 0
                total_pnl = 0.0

                for s in algo_signals:
                    outcome = self.evaluate_signal_outcome(
                        df=s['full_df'],
                        signal_index=s['signal_index'],
                        direction=s['direction'],
                        target_pct=target_pct,
                        stoploss_pct=sl,
                        max_bars=self.config.get("max_hold_bars", 187),
                        use_trailing_sl=use_trailing_sl
                    )
                    res = outcome['outcome']
                    if res == "WIN":
                        wins += 1
                    elif res == "LOSS":
                        losses += 1
                    elif res == "BREAKEVEN":
                        breakevens += 1
                    elif res == "TIMEOUT":
                        timeouts += 1
                    total_pnl += outcome['pnl_pct']

                total_trades = wins + losses + breakevens + timeouts
                win_rate = (wins / total_trades) * 100.0 if total_trades > 0 else 0.0
                loss_rate = (losses / total_trades) * 100.0 if total_trades > 0 else 0.0
                avg_pnl = total_pnl / total_trades if total_trades > 0 else 0.0
                profit_factor = (wins * target_pct) / ((losses * sl) + 1e-9)

                results.append({
                    "Algorithm": ALGORITHM_REGISTRY[algo_key](self.config).name,
                    "Algo Key": algo_key,
                    "Stop-Loss (%)": f"{sl}%",
                    "Target (%)": f"{target_pct}%",
                    "Prescreener": "ON" if use_prescreener else "OFF",
                    "Total Signals": total_trades,
                    "Wins": wins,
                    "Losses": losses,
                    "Breakevens": breakevens,
                    "Timeouts": timeouts,
                    "Win Rate (%)": round(win_rate, 2),
                    "Loss Rate (%)": round(loss_rate, 2),
                    "Avg PnL (%)": round(avg_pnl, 2),
                    "Profit Factor": round(profit_factor, 2)
                })

        res_df = pd.DataFrame(results)
        self._print_matrix(res_df)
        res_df.to_csv("accuracy_report.csv", index=False)
        print("Full accuracy report saved to: accuracy_report.csv\n")
        return res_df

    def _print_matrix(self, df: pd.DataFrame):
        if df.empty:
            return

        print("===============================================================================================================================")
        print("                                     ACCURACY & STOP-LOSS SENSITIVITY MATRIX                                                   ")
        print("===============================================================================================================================")
        header = f"{'Algorithm':<35} | {'SL %':<6} | {'Signals':<7} | {'Win Rate %':<10} | {'Loss %':<8} | {'BE %':<6} | {'Avg PnL %':<9} | {'Profit Factor':<13}"
        print(header)
        print("=" * len(header))
        for _, r in df.iterrows():
            be_rate = (r['Breakevens'] / r['Total Signals']) * 100.0 if r['Total Signals'] > 0 else 0.0
            row = f"{r['Algorithm']:<35} | {r['Stop-Loss (%)']:<6} | {r['Total Signals']:<7} | {r['Win Rate (%)']:<10.2f} | {r['Loss Rate (%)']:<8.2f} | {be_rate:<6.1f} | {r['Avg PnL (%)']:<9.2f} | {r['Profit Factor']:<13.2f}"
            print(row)
        print("=" * len(header))

def main():
    parser = argparse.ArgumentParser(description="Evaluate Accuracy & Stop-Loss Sensitivity for Screener Algos")
    parser.add_argument('--config', default='config.json', help='Path to config file')
    parser.add_argument('--lookback', type=int, default=60, help='Number of historical days to backtest (default: 60)')
    parser.add_argument('--target', type=float, default=5.0, help='Target profit percentage (default: 5.0)')
    parser.add_argument('--hold-days', type=float, default=2.5, help='Maximum holding period in days before timeout (default: 2.5)')
    parser.add_argument('--stoploss', type=float, nargs='+', default=[2.0, 3.0], help='List of stop-loss percentages (default: 2.0 3.0)')
    parser.add_argument('--no-trailing', action='store_true', help='Disable trailing stop loss')
    parser.add_argument('--no-prescreener', action='store_true', help='Disable Top-Down Sector & Index Prescreener')
    parser.add_argument('--synthetic', action='store_true', help='Use synthetic market candle simulation if API tokens expired')
    args = parser.parse_args()

    client = None
    if not args.synthetic:
        with open(args.config, 'r') as f:
            full_cfg = json.load(f)
        creds = full_cfg.get("credentials", {})
        client = SmartAPIClient(
            api_key=creds.get("api_key"),
            client_code=creds.get("client_code"),
            secret_key=creds.get("secret_key")
        )
        if not client.login():
            print("Notice: API tokens expired/invalid.")
            return

    max_bars = int(args.hold_days * 75)
    evaluator = AccuracyEvaluator(api_client=client, config_path=args.config)
    evaluator.config["max_hold_bars"] = max_bars
    evaluator.run_backtest(
        stoploss_pcts=args.stoploss,
        target_pct=args.target,
        lookback_days=args.lookback,
        use_synthetic=args.synthetic,
        use_trailing_sl=not args.no_trailing,
        use_prescreener=not args.no_prescreener
    )

if __name__ == "__main__":
    main()
