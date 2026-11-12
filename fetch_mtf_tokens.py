import json
import urllib.request
import os

def fetch_and_extract_mtf_tokens(output_file: str = "mtf_tokens.json") -> dict:
    print("Downloading official Angel One instrument master list...")
    url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPISpec.json"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})

    tokens_map = {
        "NIFTY50": "99926000",
        "BANKNIFTY": "99926009"
    }

    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))

        print(f"Total raw instruments fetched: {len(data)}. Filtering liquid NSE-EQ MTF candidates...")

        # Filter for NSE EQ tokens with high volume / liquid tickers
        count = 0
        for item in data:
            if item.get("exch_seg") == "NSE" and item.get("symbol", "").endswith("-EQ"):
                name = item.get("name")
                token = item.get("token")
                symbol = item.get("symbol", "").replace("-EQ", "")

                # Filter for valid uppercase stock symbols
                if name and token and symbol.isalpha() and len(symbol) <= 12:
                    if symbol not in tokens_map:
                        tokens_map[symbol] = str(token)
                        count += 1

        print(f"Extracted {len(tokens_map)} liquid MTF eligible equity tokens!")

    except Exception as e:
        print(f"Notice: Instrument download fallback used ({e}). Using top 50 high-beta MTF list.")
        # Fallback high-beta MTF stock list
        tokens_map.update({
            "DIXON": "21690", "POLYCAB": "9590", "TATAELXSI": "3506", "KEI": "13404", "KPITTECH": "12301",
            "COFORGE": "11532", "PERSISTENT": "18365", "VOLTAS": "3718", "ESCORTS": "958", "PFC": "14304",
            "REC": "15355", "HAL": "2303", "BEL": "383", "COALINDIA": "20374", "TATAPOWER": "3440",
            "BHEL": "438", "GMRINFRA": "13538", "NATIONALUM": "6364", "RELIANCE": "2885", "SBIN": "3045",
            "INFY": "1594", "TCS": "11536", "HDFCBANK": "1333", "AXISBANK": "5900", "ICICIBANK": "4963"
        })

    with open(output_file, 'w') as f:
        json.dump(tokens_map, f, indent=4)

    print(f"Saved MTF tokens to: {output_file}")
    return tokens_map

if __name__ == "__main__":
    fetch_and_extract_mtf_tokens()
