from risk_manager import PreTradeRiskManager

def test_risk_checks():
    ptrm = PreTradeRiskManager(
        max_single_order_value_rs=200000.0,
        max_daily_loss_pct=3.0,
        max_single_stock_pct=20.0,
        max_bid_ask_spread_pct=0.5,
        signal_debounce_seconds=300
    )
    ptrm.initialize_day_equity(1000000.0)

    # Test 1: Valid Order
    ok, msg = ptrm.validate_order("DIXON", 100000.0, 0.0, 1000000.0, bid_price=14840.0, ask_price=14850.0)
    print(f"Test 1 (Normal Order)       : Approved={ok} | Message={msg}")
    assert ok == True

    # Test 2: Fat Finger Order
    ok, msg = ptrm.validate_order("DIXON", 500000.0, 0.0, 1000000.0)
    print(f"Test 2 (Fat-Finger Guard)   : Approved={ok} | Message={msg}")
    assert ok == False

    # Test 3: Duplicate Signal Debounce
    ok, msg = ptrm.validate_order("DIXON", 100000.0, 0.0, 1000000.0)
    print(f"Test 3 (Debounce Guard)     : Approved={ok} | Message={msg}")
    assert ok == False

    # Test 4: Illiquid Bid-Ask Spread
    ok, msg = ptrm.validate_order("POLYCAB", 100000.0, 0.0, 1000000.0, bid_price=100.0, ask_price=102.0)
    print(f"Test 4 (Spread Filter)      : Approved={ok} | Message={msg}")
    assert ok == False

    # Test 5: Daily Loss Kill Switch
    ptrm.update_realized_pnl(-35000.0)  # 3.5% Loss
    ok, msg = ptrm.validate_order("HAL", 100000.0, 0.0, 1000000.0)
    print(f"Test 5 (Kill-Switch Active) : Approved={ok} | Message={msg}")
    assert ok == False

    print("\n✅ All PTRM Risk Checks Passed Successfully!")

if __name__ == "__main__":
    test_risk_checks()
