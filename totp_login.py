import json
import sys
from SmartApi import SmartConnect

def login_with_totp(totp_code: str):
    with open("config.json", "r") as f:
        config = json.load(f)
    creds = config.get("credentials", {})

    api_key = creds.get("api_key")
    client_code = creds.get("client_code")
    mpin = creds.get("mpin")

    print(f"Authenticating with Angel One SmartAPI for Client {client_code} using TOTP {totp_code}...")

    smart_api = SmartConnect(api_key=api_key)
    session = smart_api.generateSession(client_code, mpin, totp_code)
    print(f"Debug Session Response: {session}")

    if session and session.get("status"):
        data = session.get("data", {})
        jwt_token = data.get("jwtToken")
        feed_token = smart_api.getfeedToken()
        refresh_token = data.get("refreshToken")

        tokens_data = {
            "jwtToken": jwt_token,
            "feedToken": feed_token,
            "refreshToken": refresh_token
        }
        with open("tokens.json", "w") as f:
            json.dump(tokens_data, f, indent=2)
        print("✅ Session generated successfully! Updated tokens.json.")
        return True
    else:
        print(f"❌ Session generation failed. Response: {session}")
        return False

if __name__ == "__main__":
    totp = sys.argv[1] if len(sys.argv) > 1 else "224931"
    login_with_totp(totp)
