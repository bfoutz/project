import requests
import time
import math
from datetime import datetime, timezone
import os
from dotenv import load_dotenv
from tabulate import tabulate

# Load environment variables
load_dotenv()

CLIENT_ID = os.getenv("TASTY_CLIENT_ID")
CLIENT_SECRET = os.getenv("TASTY_CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("TASTY_REFRESH_TOKEN")
BASE_URL = os.getenv("TASTY_BASE_URL", "https://api.tastytrade.com")

if not all([CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN]):
    raise ValueError("Missing one or more env variables: TASTY_CLIENT_ID, TASTY_CLIENT_SECRET, TASTY_REFRESH_TOKEN")

class TastySession:
    def __init__(self):
        self.access_token = None
        self.expires_at = 0

    def refresh_token(self):
        url = f"{BASE_URL}/oauth/token"
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": REFRESH_TOKEN,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        }
        resp = requests.post(url, data=payload)
        resp.raise_for_status()
        data = resp.json()
        self.access_token = data["access_token"]
        self.expires_at = time.time() + data.get("expires_in", 3600) - 60

    def get_headers(self):
        if time.time() >= self.expires_at:
            self.refresh_token()
        return {"Authorization": f"Bearer {self.access_token}"}

session = TastySession()

def get_market_metrics(symbols):
    url = f"{BASE_URL}/market-metrics?symbols={','.join(symbols)}"
    headers = session.get_headers()
    resp = requests.get(url, headers=headers)
    
    if resp.status_code != 200:
        print(f"Error {resp.status_code}: {resp.text}")
        resp.raise_for_status()
    
    raw_data = resp.json()
    
    if isinstance(raw_data, dict) and "data" in raw_data:
        inner = raw_data["data"]
        if isinstance(inner, dict) and "items" in inner:
            return inner["items"]
    
    if isinstance(raw_data, list):
        return raw_data
    
    print("Unexpected response structure")
    return []

def calculate_dte(exp_date_str):
    try:
        if 'T' in exp_date_str:
            dt = datetime.fromisoformat(exp_date_str.replace("Z", "+00:00"))
        else:
            dt = datetime.fromisoformat(exp_date_str).replace(tzinfo=timezone.utc)
        
        today = datetime.now(timezone.utc)
        return (dt - today).days
    except ValueError:
        return -1

def interpolate_iv_with_dte(target_dte, expirations):
    expirations = [e for e in expirations if e["dte"] > 0]
    if not expirations:
        return None, None
    expirations.sort(key=lambda x: x["dte"])
    
    if len(expirations) == 1:
        if abs(expirations[0]["dte"] - target_dte) <= 15:
            return expirations[0]["iv"], expirations[0]["exp_date"]
        return None, None
    
    for i in range(len(expirations) - 1):
        low = expirations[i]
        high = expirations[i + 1]
        if low["dte"] <= target_dte <= high["dte"]:
            if high["dte"] == low["dte"]:
                return low["iv"], low["exp_date"]
            frac = (target_dte - low["dte"]) / (high["dte"] - low["dte"])
            iv = low["iv"] + frac * (high["iv"] - low["iv"])
            # Approximate date (linear between low and high dates would be more complex; using low for simplicity)
            return iv, low["exp_date"]  # You can improve this later if needed
    return None, None

def compute_forward_factor(iv_30, iv_60, dte_30, dte_60):
    if iv_30 is None or iv_60 is None or iv_60 <= 0 or dte_60 <= dte_30 or dte_30 <= 0:
        return None
    
    sigma1 = iv_30
    sigma2 = iv_60
    T1 = dte_30 / 365.0
    T2 = dte_60 / 365.0
    
    if T2 <= T1:
        return None
    
    numerator = (sigma2**2 * T2) - (sigma1**2 * T1)
    denominator = T2 - T1
    
    if denominator <= 0:
        return None
    
    forward_variance = numerator / denominator
    if forward_variance < 0:
        return None
    
    sigma_fwd = math.sqrt(forward_variance)
    ff = (sigma1 - sigma_fwd) / sigma_fwd
    return ff * 100

# Your tickers
tickers = ["USO", "TSLA"]  # ← add more here as desired

print(f"Scanning {len(tickers)} symbols...")

try:
    metrics_data = get_market_metrics(tickers)
except Exception as e:
    print("Failed to fetch metrics:", e)
    exit(1)

results = []
for item in metrics_data:
    if not isinstance(item, dict):
        continue
    
    symbol = item.get("symbol")
    if not symbol:
        continue
    
    expirations_raw = item.get("option-expiration-implied-volatilities", [])
    if not expirations_raw:
        continue
    
    exp_list = []
    for exp in expirations_raw:
        dte = calculate_dte(exp["expiration-date"])
        if dte > 0:
            iv_str = exp.get("implied-volatility")
            if iv_str is not None:
                try:
                    iv_float = float(iv_str)
                    exp_list.append({
                        "dte": dte,
                        "iv": iv_float,
                        "exp_date": exp["expiration-date"]
                    })
                except ValueError:
                    continue
    
    if len(exp_list) < 2:
        continue
    
    iv_30, date_30 = interpolate_iv_with_dte(30, exp_list)
    iv_60, date_60 = interpolate_iv_with_dte(60, exp_list)
    
    ff_pct = compute_forward_factor(iv_30, iv_60, 
                                   dte_30 = 30 if iv_30 else None,   # fallback if interp failed
                                   dte_60 = 60 if iv_60 else None)
    
    if ff_pct is not None:
        # Use actual dates in headers
        header_30 = f"IV {date_30.split('T')[0] or 'N/A'} (~30 DTE)" if date_30 else "IV ~30 DTE"
        header_60 = f"IV {date_60.split('T')[0] or 'N/A'} (~60 DTE)" if date_60 else "IV ~60 DTE"
        
        results.append({
            "Symbol": symbol,
            header_30: f"{iv_30*100:.2f}%" if iv_30 else "N/A",
            header_60: f"{iv_60*100:.2f}%" if iv_60 else "N/A",
            "Forward Factor": f"{ff_pct:.2f}%"
        })

if results:
    print("\nResults:")
    print(tabulate(results, headers="keys", tablefmt="pretty"))
else:
    print("\nNo valid Forward Factor results found.")

print("\nDone.")