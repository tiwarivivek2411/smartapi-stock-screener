import json
import webbrowser
from urllib.parse import urlparse, parse_qs
from SmartApi import SmartConnect

def main():
    with open("config.json", "r") as f:
        config = json.load(f)
    creds = config.get("credentials", {})
    
    api_key = creds.get("api_key")
    client_code = creds.get("client_code")

    login_url = f"https://smartapi.angelone.in/publisher-login?api_key={api_key}"
    print(f"\n==================================================================")
    print(f"             ANGEL ONE SMART API LOGIN HELPER                     ")
    print(f"==================================================================")
    print(f"1. Opening browser at:\n   {login_url}\n")
    print(f"2. Log in with your Angel One account ({client_code}).")
    print(f"3. After login, COPY the resulting URL from your browser address bar.")
    print(f"==================================================================\n")

    webbrowser.open(login_url)
    redirected_url = input("Paste the redirected URL here: ").strip()

    parsed = urlparse(redirected_url)
    params = parse_qs(parsed.query)
    if not params:
        params = parse_qs(parsed.fragment)

    auth_token = params.get('auth_token', [None])[0]
    feed_token = params.get('feed_token', [None])[0]
    refresh_token = params.get('refresh_token', [None])[0]

    if auth_token:
        tokens_data = {
            "jwtToken": auth_token,
            "feedToken": feed_token,
            "refreshToken": refresh_token
        }
        with open("tokens.json", "w") as f:
            json.dump(tokens_data, f, indent=2)
        print("\n✅ Successfully updated tokens.json! You are ready to run accuracy evaluation on live data.")
    else:
        print("\n❌ Failed to extract auth_token from pasted URL. Please check the URL and try again.")

if __name__ == "__main__":
    main()
