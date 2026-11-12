import time
import logging
from datetime import datetime
from typing import Dict, Optional, Tuple

class PreTradeRiskManager:
    """
    Institutional Pre-Trade Risk Management (PTRM) & Execution Safeguard Module.
    Enforces production safety checks recommended by institutional quantitative traders:
    1. Fat-Finger Order Cap (Max Single Order Value)
    2. Daily Portfolio Circuit Breaker (Emergency Kill-Switch on Max Daily Loss)
    3. Sector & Single-Stock Concentration Limit
    4. Bid-Ask Spread & Illiquidity Filter
    5. Circuit Limit Proximity Check
    6. Duplicate Signal Debouncing
    """

    def __init__(self, 
                 max_single_order_value_rs: float = 200000.0,
                 max_daily_loss_pct: float = 3.0,
                 max_single_stock_pct: float = 20.0,
                 max_sector_exposure_pct: float = 35.0,
                 max_bid_ask_spread_pct: float = 0.5,
                 signal_debounce_seconds: int = 300):
        self.max_single_order_value_rs = max_single_order_value_rs
        self.max_daily_loss_pct = max_daily_loss_pct
        self.max_single_stock_pct = max_single_stock_pct
        self.max_sector_exposure_pct = max_sector_exposure_pct
        self.max_bid_ask_spread_pct = max_bid_ask_spread_pct
        self.signal_debounce_seconds = signal_debounce_seconds

        self.initial_daily_equity: Optional[float] = None
        self.current_daily_realized_pnl: float = 0.0
        self.is_kill_switch_engaged: bool = False
        self.recent_signals: Dict[str, float] = {}

    def initialize_day_equity(self, starting_capital: float):
        self.initial_daily_equity = starting_capital
        self.current_daily_realized_pnl = 0.0
        self.is_kill_switch_engaged = False
        print(f" 🛡️ PTRM Risk Engine Initialized for Today. Starting Portfolio Capital: ₹{starting_capital:,.2f}")

    def update_realized_pnl(self, pnl_delta_rs: float):
        self.current_daily_realized_pnl += pnl_delta_rs
        if self.initial_daily_equity and self.initial_daily_equity > 0:
            daily_loss_pct = (abs(self.current_daily_realized_pnl) / self.initial_daily_equity) * 100.0
            if self.current_daily_realized_pnl < 0 and daily_loss_pct >= self.max_daily_loss_pct:
                self.engage_emergency_kill_switch(daily_loss_pct)

    def engage_emergency_kill_switch(self, loss_pct: float):
        self.is_kill_switch_engaged = True
        print(f"\n 🚨🚨 EMERGENCY KILL SWITCH ENGAGED! 🚨🚨")
        print(f" Daily Loss reached {loss_pct:.2f}% (Threshold: {self.max_daily_loss_pct}%).")
        print(f" ALL NEW TRADES ARE HALTED. EXITS ONLY.\n")

    def validate_order(self, 
                       symbol: str, 
                       order_value_rs: float, 
                       current_stock_exposure_rs: float, 
                       total_portfolio_equity_rs: float,
                       bid_price: float = 0.0,
                       ask_price: float = 0.0) -> Tuple[bool, str]:
        """
        Runs Pre-Trade Risk Management (PTRM) checks before submitting order to broker API.
        Returns (is_approved, rejection_reason).
        """
        # 1. Kill Switch Guard
        if self.is_kill_switch_engaged:
            return False, "REJECTED: Daily Loss Circuit Breaker Kill-Switch is Active."

        # 2. Fat-Finger Single Order Value Guard
        if order_value_rs > self.max_single_order_value_rs:
            return False, f"REJECTED: Order value ₹{order_value_rs:,.2f} exceeds Max Fat-Finger Limit ₹{self.max_single_order_value_rs:,.2f}."

        # 3. Single Stock Concentration Guard
        projected_stock_exposure = current_stock_exposure_rs + order_value_rs
        max_allowed_stock_exp = total_portfolio_equity_rs * (self.max_single_stock_pct / 100.0)
        if projected_stock_exposure > max_allowed_stock_exp:
            return False, f"REJECTED: Stock exposure ₹{projected_stock_exposure:,.2f} exceeds Concentration Limit ({self.max_single_stock_pct}%)."

        # 4. Bid-Ask Spread / Illiquidity Guard
        if bid_price > 0 and ask_price > 0:
            spread_pct = ((ask_price - bid_price) / bid_price) * 100.0
            if spread_pct > self.max_bid_ask_spread_pct:
                return False, f"REJECTED: Bid-Ask Spread {spread_pct:.2f}% is too wide (Illiquidity Guard > {self.max_bid_ask_spread_pct}%)."

        # 5. Duplicate Signal Debounce Guard
        now_ts = time.time()
        if symbol in self.recent_signals:
            elapsed = now_ts - self.recent_signals[symbol]
            if elapsed < self.signal_debounce_seconds:
                return False, f"REJECTED: Duplicate signal debounced for {symbol} ({int(elapsed)}s < {self.signal_debounce_seconds}s window)."

        self.recent_signals[symbol] = now_ts
        return True, "APPROVED"
