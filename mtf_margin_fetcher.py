import json
import urllib.request
import os

class MTFMarginFetcher:
    def __init__(self, cache_file: str = "mtf_stock_multipliers.json"):
        self.cache_file = cache_file
        self.stock_multipliers = self._load_cache()

    def _load_cache(self) -> dict:
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def fetch_angelone_mtf_multipliers(self) -> dict:
        print("Fetching stock-specific MTF margin multipliers from Angel One margin API...")
        url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPISpec.json"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})

        multipliers = {}
        try:
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode('utf-8'))

            for item in data:
                if item.get("exch_seg") == "NSE" and item.get("symbol", "").endswith("-EQ"):
                    symbol = item.get("symbol", "").replace("-EQ", "")
                    # Angel One margin haircut % or var margin %
                    haircut_pct = float(item.get("haircut", 25.0) or 25.0)
                    if haircut_pct <= 0:
                        haircut_pct = 25.0

                    # Multiplier = 100 / haircut_pct (e.g., 20% margin -> 5.0x multiplier, 25% -> 4.0x)
                    multiplier = round(100.0 / haircut_pct, 2)
                    # Bound multiplier between 2.0x and 5.0x (standard Indian MTF limits)
                    multiplier = max(2.0, min(5.0, multiplier))
                    multipliers[symbol] = multiplier

            print(f"Extracted stock-specific MTF multipliers for {len(multipliers)} stocks from Angel One!")

        except Exception as e:
            print(f"Notice: Margin calculator fetch fallback ({e}). Using standard stock-specific lookup.")
            # Default stock-specific MTF multipliers from Angel One margin list
            multipliers = {
                "DIXON": 5.0, "POLYCAB": 4.0, "TATAELXSI": 4.0, "KEI": 4.0, "KPITTECH": 4.0,
                "COFORGE": 4.0, "PERSISTENT": 4.0, "VOLTAS": 4.0, "ESCORTS": 4.0, "PFC": 4.0,
                "REC": 4.0, "HAL": 5.0, "BEL": 5.0, "COALINDIA": 4.0, "TATAPOWER": 4.0,
                "BHEL": 3.5, "GMRINFRA": 3.5, "NATIONALUM": 4.0, "RELIANCE": 5.0, "SBIN": 5.0,
                "INFY": 5.0, "TCS": 5.0, "HDFCBANK": 5.0, "AXISBANK": 5.0, "ICICIBANK": 5.0
            }

        self.stock_multipliers = multipliers
        with open(self.cache_file, 'w') as f:
            json.dump(multipliers, f, indent=4)

        return multipliers

    def get_stock_mtf_multiplier(self, symbol: str) -> float:
        if not self.stock_multipliers:
            self.fetch_angelone_mtf_multipliers()
        return self.stock_multipliers.get(symbol, 4.0)

if __name__ == "__main__":
    fetcher = MTFMarginFetcher()
    res = fetcher.fetch_angelone_mtf_multipliers()
    print("Sample Stock MTF Multipliers:")
    for sym in ["DIXON", "HAL", "BEL", "POLYCAB", "BHEL"]:
        print(f"  {sym}: {res.get(sym, 4.0)}x")
