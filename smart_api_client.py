import os
import json
import time
import requests
import pandas as pd
from datetime import datetime
from SmartApi import SmartConnect

def get_public_ip():
    try:
        return requests.get('https://api.ipify.org').text
    except Exception:
        return "127.0.0.1"

class SmartAPIClient:
    def __init__(self, api_key: str, client_code: str, secret_key: str):
        self.api_key = api_key
        self.client_code = client_code
        self.secret_key = secret_key
        self.public_ip = get_public_ip()
        self.smart_api = SmartConnect(api_key=self.api_key)
        self.session_data = None
        self.auth_token = None
        self.refresh_token = None
        self.feed_token = None

    def login(self) -> bool:
        """
        Attempts to load saved tokens from tokens.json or perform login.
        """
        if self._load_tokens():
            print("Successfully authenticated using saved session tokens.")
            return True
        print("No valid session tokens found. Please run authentication.")
        return False

    def _load_tokens(self) -> bool:
        if not os.path.exists("tokens.json"):
            return False
        try:
            with open("tokens.json", "r") as f:
                data = json.load(f)
            self.session_data = data
            self.auth_token = data.get("jwtToken")
            self.feed_token = data.get("feedToken")
            self.refresh_token = data.get("refreshToken")

            if not self.auth_token:
                return False

            raw_jwt = self.auth_token.replace("Bearer ", "").strip()
            self.smart_api.setAccessToken(raw_jwt)
            self.smart_api.setFeedToken(self.feed_token)
            self.smart_api.setRefreshToken(self.refresh_token)
            self.smart_api.setUserId(self.client_code)
            return True
        except Exception as e:
            print(f"Error loading tokens: {e}")
            return False

    def fetch_historical_data(self, token: str, interval: str, from_date: str, to_date: str, exchange: str = "NSE") -> pd.DataFrame:
        """
        Fetches 5-minute historical candle data with automatic chunking and disk caching.
        """
        try:
            cache_dir = os.path.join("data", "cache")
            os.makedirs(cache_dir, exist_ok=True)

            f_clean = from_date.replace(" ", "_").replace(":", "")
            t_clean = to_date.replace(" ", "_").replace(":", "")
            cache_file = os.path.join(cache_dir, f"{token}_{interval}_{f_clean}_{t_clean}.csv")

            if os.path.exists(cache_file):
                df = pd.read_csv(cache_file)
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                return df

            start_dt = datetime.strptime(from_date, "%Y-%m-%d %H:%M")
            end_dt = datetime.strptime(to_date, "%Y-%m-%d %H:%M")
            max_days = 20 if "MINUTE" in interval else 90

            all_dfs = []
            current_start = start_dt

            while current_start < end_dt:
                current_end = current_start + pd.Timedelta(days=max_days)
                if current_end > end_dt:
                    current_end = end_dt

                f_date = current_start.strftime("%Y-%m-%d %H:%M")
                t_date = current_end.strftime("%Y-%m-%d %H:%M")

                historic_param = {
                    "exchange": exchange,
                    "symboltoken": token,
                    "interval": interval,
                    "fromdate": f_date,
                    "todate": t_date
                }

                data = self.smart_api.getCandleData(historic_param)

                if data and isinstance(data, dict) and data.get('status') and data.get('data'):
                    columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
                    chunk_df = pd.DataFrame(data['data'], columns=columns)
                    chunk_df['timestamp'] = pd.to_datetime(chunk_df['timestamp'])
                    chunk_df[['open', 'high', 'low', 'close', 'volume']] = chunk_df[
                        ['open', 'high', 'low', 'close', 'volume']
                    ].apply(pd.to_numeric)
                    all_dfs.append(chunk_df)

                minute_map = {
                    "ONE_MINUTE": 1, "THREE_MINUTE": 3, "FIVE_MINUTE": 5,
                    "FIFTEEN_MINUTE": 15, "THIRTY_MINUTE": 30, "ONE_HOUR": 60,
                    "ONE_DAY": 1440
                }
                delta_mins = minute_map.get(interval, 1440)
                current_start = current_end + pd.Timedelta(minutes=delta_mins)
                time.sleep(0.3)

            if not all_dfs:
                return pd.DataFrame()

            final_df = pd.concat(all_dfs).drop_duplicates(subset=['timestamp']).sort_values('timestamp').reset_index(drop=True)
            final_df.to_csv(cache_file, index=False)
            return final_df

        except Exception as e:
            print(f"Error fetching historical data for token {token}: {e}")
            return pd.DataFrame()
