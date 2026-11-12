import json
import os
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional
from algorithms import ALGORITHM_REGISTRY
from mtf_margin_fetcher import MTFMarginFetcher

PARAM_MODES = {
    "fixed_2_1": {"target_pct": 2.0, "stoploss_pct": 1.0, "use_trailing": False, "auto_squareoff_3pm": False, "label": "Fixed 2&1 (Target +2% | SL 1%)"},
    "trailing_2_1": {"target_pct": 2.0, "stoploss_pct": 1.0, "use_trailing": True, "auto_squareoff_3pm": False, "label": "Trailing 2&1 (Target +2% | SL 1%)"},
    "fixed_3_1": {"target_pct": 3.0, "stoploss_pct": 1.0, "use_trailing": False, "auto_squareoff_3pm": False, "label": "Fixed 3&1 (Target +3% | SL 1%)"},
    "trailing_3_1": {"target_pct": 3.0, "stoploss_pct": 1.0, "use_trailing": True, "auto_squareoff_3pm": False, "label": "Trailing 3&1 (Target +3% | SL 1%)"},
    "fixed_3_2": {"target_pct": 3.0, "stoploss_pct": 2.0, "use_trailing": False, "auto_squareoff_3pm": False, "label": "Fixed 3&2 (Target +3% | SL 2%)"},
    "trailing_3_2": {"target_pct": 3.0, "stoploss_pct": 2.0, "use_trailing": True, "auto_squareoff_3pm": False, "label": "Trailing 3&2 (Target +3% | SL 2%)"},
    "fixed_4_2": {"target_pct": 4.0, "stoploss_pct": 2.0, "use_trailing": False, "auto_squareoff_3pm": False, "label": "Fixed 4&2 (Target +4% | SL 2%)"},
    "trailing_4_2": {"target_pct": 4.0, "stoploss_pct": 2.0, "use_trailing": True, "auto_squareoff_3pm": False, "label": "Trailing 4&2 (Target +4% | SL 2%)"},
    "fixed_5_2": {"target_pct": 5.0, "stoploss_pct": 2.0, "use_trailing": False, "auto_squareoff_3pm": False, "label": "Fixed 5&2 (Target +5% | SL 2%)"},
    "trailing_5_2": {"target_pct": 5.0, "stoploss_pct": 2.0, "use_trailing": True, "auto_squareoff_3pm": False, "label": "Trailing 5&2 (Target +5% | SL 2%)"},
    "fixed_6_2": {"target_pct": 6.0, "stoploss_pct": 2.0, "use_trailing": False, "auto_squareoff_3pm": False, "label": "Fixed 6&2 (Target +6% | SL 2%)"},
    "trailing_6_2": {"target_pct": 6.0, "stoploss_pct": 2.0, "use_trailing": True, "auto_squareoff_3pm": False, "label": "Trailing 6&2 (Target +6% | SL 2%)"},
    "fixed_5_3": {"target_pct": 5.0, "stoploss_pct": 3.0, "use_trailing": False, "auto_squareoff_3pm": False, "label": "Fixed 5&3 (Target +5% | SL 3%)"},
    "trailing_5_3": {"target_pct": 5.0, "stoploss_pct": 3.0, "use_trailing": True, "auto_squareoff_3pm": False, "label": "Trailing 5&3 (Target +5% | SL 3%)"},
    "fixed_6_3": {"target_pct": 6.0, "stoploss_pct": 3.0, "use_trailing": False, "auto_squareoff_3pm": False, "label": "Fixed 6&3 (Target +6% | SL 3%)"},
    "trailing_6_3": {"target_pct": 6.0, "stoploss_pct": 3.0, "use_trailing": True, "auto_squareoff_3pm": False, "label": "Trailing 6&3 (Target +6% | SL 3%)"},
    "trailing_no_tp": {"target_pct": 999.0, "stoploss_pct": 2.0, "use_trailing": True, "auto_squareoff_3pm": False, "label": "Unlimited Trailing Runner (No TP)"},
    "intraday_3pm": {"target_pct": 1.5, "stoploss_pct": 1.5, "use_trailing": True, "auto_squareoff_3pm": True, "label": "Intraday 3:00 PM (+1.5% TP / 1.5% SL)"}
}

class SingleModeTrader:
    def __init__(self, algo_key: str, algo_name: str, mode_key: str, mode_cfg: dict, initial_capital: float = 500000.0, db_dir: str = "db"):
        self.algo_key = algo_key
        self.algo_name = algo_name
        self.mode_key = mode_key
        self.mode_cfg = mode_cfg
        self.initial_capital = initial_capital
        self.current_equity = initial_capital
        self.current_mtf_equity = initial_capital
        self.db_dir = db_dir
        self.margin_fetcher = MTFMarginFetcher()

        self.orderbooks_dir = os.path.join(self.db_dir, "orderbooks")
        os.makedirs(self.orderbooks_dir, exist_ok=True)

        self.trades_file = os.path.join(self.orderbooks_dir, f"paper_trades_{self.algo_key}_{self.mode_key}.json")
        self.csv_file = os.path.join(self.orderbooks_dir, f"paper_trades_{self.algo_key}_{self.mode_key}.csv")

        self.open_positions: List[Dict] = []
        self.closed_positions: List[Dict] = []
        self.order_counter = 1001
        self._load_state()

    def _load_state(self):
        if os.path.exists(self.trades_file):
            try:
                with open(self.trades_file, 'r') as f:
                    data = json.load(f)
                    self.current_equity = data.get("current_equity", self.initial_capital)
                    self.current_mtf_equity = data.get("current_mtf_equity", self.initial_capital)
                    self.open_positions = data.get("open_positions", [])
                    self.closed_positions = data.get("closed_positions", [])
                    self.order_counter = data.get("order_counter", 1001)
            except Exception:
                pass

    def _save_state(self):
        data = {
            "algo_key": self.algo_key,
            "algo_name": self.algo_name,
            "mode_key": self.mode_key,
            "mode_label": self.mode_cfg["label"],
            "initial_capital": self.initial_capital,
            "current_equity": round(self.current_equity, 2),
            "current_mtf_equity": round(self.current_mtf_equity, 2),
            "order_counter": self.order_counter,
            "open_positions": self.open_positions,
            "closed_positions": self.closed_positions,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        with open(self.trades_file, 'w') as f:
            json.dump(data, f, indent=4)

        all_trades = self.open_positions + self.closed_positions
        if all_trades:
            df = pd.DataFrame(all_trades)
            df.to_csv(self.csv_file, index=False)

    def execute_dummy_trade(self, symbol: str, token: str, price: float, direction: str = "BULLISH", max_positions: int = 5) -> Optional[Dict]:
        for pos in self.open_positions:
            if pos['symbol'] == symbol:
                return None

        if len(self.open_positions) >= max_positions:
            return None

        # Short selling allowed ONLY for Intraday mode
        if direction == "BEARISH" and not self.mode_cfg["auto_squareoff_3pm"]:
            return None

        stock_mtf_mult = self.margin_fetcher.get_stock_mtf_multiplier(symbol)
        margin_capital = 100000.0  # ₹1,00,000 cash margin
        leveraged_buying_power = margin_capital * stock_mtf_mult
        qty = int(leveraged_buying_power / price)
        if qty <= 0:
            return None

        actual_investment = round(qty * price, 2)
        target_pct = self.mode_cfg['target_pct']
        stoploss_pct = self.mode_cfg['stoploss_pct']

        if direction == "BULLISH":
            action = "BUY"
            target_price = round(price * (1.0 + (target_pct / 100.0)), 2)
            stop_price = round(price * (1.0 - (stoploss_pct / 100.0)), 2)
            initial_risk_per_share = price - stop_price
        else:
            action = "SELL"
            target_price = round(price * (1.0 - (target_pct / 100.0)), 2)
            stop_price = round(price * (1.0 + (stoploss_pct / 100.0)), 2)
            initial_risk_per_share = stop_price - price

        order_id = f"{self.algo_key.upper()}-{self.mode_key.upper()}-{self.order_counter}"
        self.order_counter += 1

        trade = {
            "order_id": order_id,
            "algo_key": self.algo_key,
            "algo_name": self.algo_name,
            "mode_key": self.mode_key,
            "mode_label": self.mode_cfg["label"],
            "use_trailing": self.mode_cfg["use_trailing"],
            "auto_squareoff_3pm": self.mode_cfg["auto_squareoff_3pm"],
            "symbol": symbol,
            "token": token,
            "direction": direction,
            "action": action,
            "status": "OPEN",
            "entry_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "entry_price": round(price, 2),
            "quantity": qty,
            "margin_used_rs": margin_capital,
            "angelone_mtf_multiplier": stock_mtf_mult,
            "mtf_total_exposure_rs": actual_investment,
            "target_pct": target_pct if target_pct < 900.0 else "UNLIMITED",
            "stoploss_pct": stoploss_pct,
            "target_price": target_price if target_pct < 900.0 else "NONE",
            "stop_price": stop_price,
            "initial_risk_per_share": round(initial_risk_per_share, 2),
            "extreme_price_seen": round(price, 2),
            "exit_time": None,
            "exit_price": None,
            "pnl_pct_unleveraged": None,
            "pnl_rs_unleveraged": None,
            "mtf_pnl_pct_leveraged": None,
            "mtf_pnl_rs_leveraged": None,
            "exit_reason": None
        }

        self.open_positions.append(trade)
        self._save_state()

        icon = "🚀 BUY" if action == "BUY" else "🔻 SHORT SELL"
        print(f" {icon} [{self.algo_key.upper()}:{self.mode_key}] {symbol} @ ₹{price:.2f} (Qty: {qty} | Margin: ₹{margin_capital:,.2f} | MTF {stock_mtf_mult:.1f}x)")
        return trade

    def update_open_positions(self, latest_prices: Dict[str, float]):
        if not self.open_positions:
            return

        now_dt = datetime.now()
        current_time_str = now_dt.strftime("%H:%M")
        is_past_3pm = current_time_str >= "15:00"

        still_open = []
        for pos in self.open_positions:
            symbol = pos['symbol']
            if symbol not in latest_prices:
                still_open.append(pos)
                continue

            curr_price = latest_prices[symbol]
            action = pos.get('action', 'BUY')

            if action == "BUY":
                pos['extreme_price_seen'] = max(pos.get('extreme_price_seen', pos['entry_price']), curr_price)
                peak_pnl_pct = round(((pos['extreme_price_seen'] - pos['entry_price']) / pos['entry_price']) * 100.0, 2)
                pos['max_pnl_pct_reached'] = peak_pnl_pct

                if pos.get('use_trailing', True):
                    if (pos['extreme_price_seen'] - pos['entry_price']) / pos['entry_price'] >= 0.006:
                        pos['stop_price'] = max(pos['stop_price'], pos['entry_price'])

                is_target_hit = (curr_price >= pos['target_price']) if pos['target_price'] != "NONE" else False
                is_stop_hit = curr_price <= pos['stop_price']
            else:  # SELL (SHORT)
                pos['extreme_price_seen'] = min(pos.get('extreme_price_seen', pos['entry_price']), curr_price)
                peak_pnl_pct = round(((pos['entry_price'] - pos['extreme_price_seen']) / pos['entry_price']) * 100.0, 2)
                pos['max_pnl_pct_reached'] = peak_pnl_pct

                if pos.get('use_trailing', True):
                    if (pos['entry_price'] - pos['extreme_price_seen']) / pos['entry_price'] >= 0.006:
                        pos['stop_price'] = min(pos['stop_price'], pos['entry_price'])

                is_target_hit = (curr_price <= pos['target_price']) if pos['target_price'] != "NONE" else False
                is_stop_hit = curr_price >= pos['stop_price']

            is_3pm_squareoff = pos.get('auto_squareoff_3pm', False) and is_past_3pm

            if is_target_hit or is_stop_hit or is_3pm_squareoff:
                pos['status'] = "CLOSED"
                pos['exit_time'] = now_dt.strftime("%Y-%m-%d %H:%M:%S")
                pos['exit_price'] = round(curr_price, 2)

                if action == "BUY":
                    exit_pnl_raw = ((curr_price - pos['entry_price']) / pos['entry_price']) * 100.0
                else:  # SHORT
                    exit_pnl_raw = ((pos['entry_price'] - curr_price) / pos['entry_price']) * 100.0

                if is_3pm_squareoff and not (is_target_hit or is_stop_hit):
                    pos['exit_reason'] = "INTRADAY_3PM_SQUAREOFF"
                    pnl_pct_unlev = exit_pnl_raw
                elif is_target_hit:
                    pos['exit_reason'] = "TARGET_HIT"
                    pnl_pct_unlev = float(pos['target_pct'])
                else:
                    pos['exit_reason'] = "STOP_LOSS_HIT" if exit_pnl_raw < 0 else "TRAILING_STOP_BREAKEVEN"
                    pnl_pct_unlev = exit_pnl_raw

                pnl_pct_unlev = round(pnl_pct_unlev, 2)
                pnl_rs_unlev = round((pos['mtf_total_exposure_rs'] * (pnl_pct_unlev / 100.0)), 2)

                mtf_mult = pos.get('angelone_mtf_multiplier', 4.0)
                mtf_pnl_pct = round(pnl_pct_unlev * mtf_mult, 2)
                mtf_pnl_rs = pnl_rs_unlev

                pos['pnl_pct_unleveraged'] = pnl_pct_unlev
                pos['pnl_rs_unleveraged'] = pnl_rs_unlev
                pos['mtf_pnl_pct_leveraged'] = mtf_pnl_pct
                pos['mtf_pnl_rs_leveraged'] = mtf_pnl_rs

                self.current_equity += (pos['margin_used_rs'] * (pnl_pct_unlev / 100.0))
                self.current_mtf_equity += mtf_pnl_rs
                self.closed_positions.append(pos)

                print(f" 🔔 [{self.algo_key.upper()}:{self.mode_key}] EXIT {pos['action']} {symbol} ({pos['exit_reason']}) @ ₹{curr_price:.2f} | Stock: {pnl_pct_unlev:+.2f}% | MTF {mtf_mult:.1f}x: {mtf_pnl_pct:+.2f}% (₹{mtf_pnl_rs:+,.2f})")
            else:
                still_open.append(pos)

        self.open_positions = still_open
        self._save_state()

class MultiStrategyPaperTrader:
    def __init__(self, initial_capital_per_strategy: float = 500000.0, db_dir: str = "db"):
        self.initial_capital_per_strategy = initial_capital_per_strategy
        self.db_dir = db_dir
        os.makedirs(self.db_dir, exist_ok=True)

        self.traders: Dict[str, Dict[str, SingleModeTrader]] = {}

        dummy_config = {}
        for algo_key, cls in ALGORITHM_REGISTRY.items():
            algo_name = cls(dummy_config).name
            self.traders[algo_key] = {}
            for mode_key, mode_cfg in PARAM_MODES.items():
                self.traders[algo_key][mode_key] = SingleModeTrader(
                    algo_key=algo_key,
                    algo_name=algo_name,
                    mode_key=mode_key,
                    mode_cfg=mode_cfg,
                    initial_capital=initial_capital_per_strategy,
                    db_dir=self.db_dir
                )

    def execute_signal(self, algo_key: str, symbol: str, token: str, price: float, direction: str = "BULLISH"):
        if algo_key in self.traders:
            for mode_key, trader in self.traders[algo_key].items():
                trader.execute_dummy_trade(
                    symbol=symbol,
                    token=token,
                    price=price,
                    direction=direction
                )
            self._save_dashboard_db()

    def update_all_positions(self, latest_prices: Dict[str, float]):
        for algo_dict in self.traders.values():
            for trader in algo_dict.values():
                trader.update_open_positions(latest_prices)
        self._save_dashboard_db()

    def _save_dashboard_db(self):
        dashboard_records = []
        all_open = []
        all_closed = []

        total_master_initial = len(self.traders) * len(PARAM_MODES) * self.initial_capital_per_strategy
        total_master_unlev_equity = 0.0
        total_master_mtf_equity = 0.0

        for algo_key, mode_dict in self.traders.items():
            for mode_key, trader in mode_dict.items():
                total_closed = len(trader.closed_positions)
                
                wins = len([t for t in trader.closed_positions if (t.get('pnl_pct_unleveraged') is not None and t.get('pnl_pct_unleveraged') > 0) or (t.get('mtf_pnl_rs_leveraged') is not None and t.get('mtf_pnl_rs_leveraged') > 0) or t.get('exit_reason') == 'TARGET_HIT'])
                win_rate = round((wins / total_closed) * 100.0, 2) if total_closed > 0 else 0.0

                tp_hits = len([t for t in trader.closed_positions if t.get('exit_reason') == 'TARGET_HIT'])
                tp_achieved_rate = round((tp_hits / total_closed) * 100.0, 2) if total_closed > 0 else 0.0

                unlev_profit = round(trader.current_equity - trader.initial_capital, 2)
                mtf_profit = round(trader.current_mtf_equity - trader.initial_capital, 2)

                total_master_unlev_equity += trader.current_equity
                total_master_mtf_equity += trader.current_mtf_equity

                dashboard_records.append({
                    "algo_key": algo_key,
                    "algo_name": trader.algo_name,
                    "mode_key": mode_key,
                    "mode_label": trader.mode_cfg["label"],
                    "open_positions_count": len(trader.open_positions),
                    "closed_trades_count": total_closed,
                    "win_rate_pct": win_rate,
                    "tp_achieved_rate_pct": tp_achieved_rate,
                    "unleveraged_equity_rs": round(trader.current_equity, 2),
                    "unleveraged_profit_rs": unlev_profit,
                    "mtf_leveraged_equity_rs": round(trader.current_mtf_equity, 2),
                    "mtf_leveraged_profit_rs": mtf_profit
                })

                all_open.extend(trader.open_positions)
                all_closed.extend(trader.closed_positions)

        pd.DataFrame(dashboard_records).to_csv(os.path.join(self.db_dir, "master_dashboard.csv"), index=False)

        master_db_json = {
            "total_modes_monitored": len(PARAM_MODES),
            "total_algorithms_monitored": len(self.traders),
            "master_initial_capital": total_master_initial,
            "master_unleveraged_equity": round(total_master_unlev_equity, 2),
            "master_unleveraged_profit": round(total_master_unlev_equity - total_master_initial, 2),
            "master_mtf_leveraged_equity": round(total_master_mtf_equity, 2),
            "master_mtf_leveraged_profit": round(total_master_mtf_equity - total_master_initial, 2),
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "strategies": dashboard_records
        }
        with open(os.path.join(self.db_dir, "master_dashboard.json"), 'w') as f:
            json.dump(master_db_json, f, indent=4)

        if all_open:
            pd.DataFrame(all_open).to_csv(os.path.join(self.db_dir, "open_positions_master.csv"), index=False)
            with open(os.path.join(self.db_dir, "open_positions_master.json"), 'w') as f:
                json.dump(all_open, f, indent=4)

        if all_closed:
            pd.DataFrame(all_closed).to_csv(os.path.join(self.db_dir, "closed_trades_master.csv"), index=False)
            with open(os.path.join(self.db_dir, "closed_trades_master.json"), 'w') as f:
                json.dump(all_closed, f, indent=4)

    def print_master_dashboard(self):
        self._save_dashboard_db()
        print("\n==========================================================================================================================================")
        print("     PARAMETRIC MASTER PAPER TRADING DASHBOARD (DUAL METRICS & INTRADAY SHORT SELLING ENABLED)")
        print("==========================================================================================================================================")
        header = f"{'Algorithm':<32} | {'Mode':<15} | {'Open':<4} | {'Closed':<6} | {'Win %':<6} | {'TP Hit %':<8} | {'MTF Equity (₹)':<16} | {'MTF Profit (₹)':<15}"
        print(header)
        print("=" * len(header))

        total_master_initial = len(self.traders) * len(PARAM_MODES) * self.initial_capital_per_strategy
        total_master_mtf_equity = 0.0

        for algo_key, mode_dict in self.traders.items():
            for mode_key, trader in mode_dict.items():
                total_closed = len(trader.closed_positions)
                wins = len([t for t in trader.closed_positions if (t.get('pnl_pct_unleveraged') is not None and t.get('pnl_pct_unleveraged') > 0) or (t.get('mtf_pnl_rs_leveraged') is not None and t.get('mtf_pnl_rs_leveraged') > 0) or t.get('exit_reason') == 'TARGET_HIT'])
                win_rate = (wins / total_closed) * 100.0 if total_closed > 0 else 0.0
                
                tp_hits = len([t for t in trader.closed_positions if t.get('exit_reason') == 'TARGET_HIT'])
                tp_rate = (tp_hits / total_closed) * 100.0 if total_closed > 0 else 0.0

                mtf_profit_rs = trader.current_mtf_equity - trader.initial_capital
                total_master_mtf_equity += trader.current_mtf_equity

                mtf_profit_str = f"₹{mtf_profit_rs:+,.2f}"
                row = f"{trader.algo_name:<32} | {mode_key:<15} | {len(trader.open_positions):<4} | {total_closed:<6} | {win_rate:<6.1f} | {tp_rate:<8.1f} | ₹{trader.current_mtf_equity:<15,.2f} | {mtf_profit_str:<15}"
                print(row)

        print("=" * len(header))
        master_mtf_profit = total_master_mtf_equity - total_master_initial
        print(f"GRAND MASTER PORTFOLIO (24 STRATEGIES x 6 MODES = 144 ISOLATED ORDERBOOKS): Initial: ₹{total_master_initial:,.2f} | MTF Equity: ₹{total_master_mtf_equity:,.2f} | Net MTF Profit: ₹{master_mtf_profit:+,.2f}\n")

if __name__ == "__main__":
    ms = MultiStrategyPaperTrader()
    ms.print_master_dashboard()
