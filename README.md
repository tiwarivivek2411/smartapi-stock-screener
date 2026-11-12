# 5-Minute Multi-Stock Screener (3-5% Move in 2-3 Days)

Lightweight, high-performance quantitative stock screener designed to scan 5-minute candle data across multiple stock symbols to identify high-probability candidates capable of delivering **3% to 5% price movements within 2-3 trading days**.

## Key Features

1. **5-Minute Candle Volatility Analysis**: Calculates True Range, 5-minute ATR, and Average Daily Range (ADR %).
2. **2-3 Day Potential Move Estimation**: Scales 5-minute return variance and ADR over 187.5 5-minute bars (2.5 trading days).
3. **Trend & Momentum Alignment**: Uses 5-minute EMA 20/50 alignment and RSI (14) momentum to score trend direction (BULLISH vs BEARISH).
4. **Probability Scoring Engine**: Ranks candidates based on target move potential fit (3-5% window) and trend strength.
5. **Local Caching & Authentication**: Caches historical API data in `data/cache/` to minimize API calls and re-uses session tokens.

## File Structure

- `screener.py`: Main quantitative screener logic and CLI runner.
- `smart_api_client.py`: Lightweight SmartAPI client wrapper for historical 5-minute data.
- `config.json`: Configuration settings for API credentials and screener parameters.
- `nifty50_tokens.json`: Symbol-to-token map for stock scanning.
- `test_screener.py`: Unit tests for metric calculations.
- `screener_results.csv`: Saved CSV output containing screened candidates.

## How to Run

```bash
# Run the screener
python3 screener.py

# Run unit tests
python3 test_screener.py
```
