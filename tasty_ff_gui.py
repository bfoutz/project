import requests
import time
import math
import csv
from datetime import datetime, timezone, timedelta
import os
from dotenv import load_dotenv
import tkinter as tk
from tkinter import ttk, filedialog, messagebox


# ────────────────────────────────────────────────
#  Load credentials
# ────────────────────────────────────────────────
load_dotenv()

CLIENT_ID = os.getenv("TASTY_CLIENT_ID")
CLIENT_SECRET = os.getenv("TASTY_CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("TASTY_REFRESH_TOKEN")
BASE_URL = os.getenv("TASTY_BASE_URL", "https://api.tastytrade.com")

if not all([CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN]):
    raise ValueError("Missing env variables: TASTY_CLIENT_ID / CLIENT_SECRET / REFRESH_TOKEN")

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

# ────────────────────────────────────────────────
#  Core functions
# ────────────────────────────────────────────────

def get_market_metrics(symbols):
    if not symbols:
        return []
    url = f"{BASE_URL}/market-metrics?symbols={','.join(symbols)}"
    headers = session.get_headers()
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        raise Exception(f"API error {resp.status_code}: {resp.text}")

    raw = resp.json()
    if isinstance(raw, dict) and "data" in raw:
        inner = raw["data"]
        if isinstance(inner, dict) and "items" in inner:
            return inner["items"]
    if isinstance(raw, list):
        return raw
    return []

def get_expirations_for_spy():
    """Fetch all available expiration dates for SPY"""
    symbol = "SPY"
    url = f"{BASE_URL}/option-chains/{symbol}/nested"
    headers = session.get_headers()
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        return []

    raw = resp.json()
    expirations = []
    for item in raw.get("data", {}).get("items", []):
        for exp in item.get("expirations", []):
            date_str = exp.get("expiration-date", "").split("T")[0]
            if date_str:
                expirations.append(date_str)
    return sorted(set(expirations))  # unique, sorted

def calculate_dte(exp_date_str):
    try:
        if 'T' in exp_date_str:
            dt = datetime.fromisoformat(exp_date_str.replace("Z", "+00:00"))
        else:
            dt = datetime.fromisoformat(exp_date_str).replace(tzinfo=timezone.utc)
        today = datetime.now(timezone.utc)
        return (dt - today).days
    except:
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
            frac = (target_dte - low["dte"]) / (high["dte"] - low["dte"])
            iv = low["iv"] + frac * (high["iv"] - low["iv"])
            return iv, low["exp_date"]
    return None, None

def compute_forward_factor(iv_short, iv_long, dte_short, dte_long):
    if any(x is None for x in [iv_short, iv_long, dte_short, dte_long]):
        return None
    if iv_long <= 0 or dte_long <= dte_short or dte_short <= 0:
        return None

    sigma1 = iv_short
    sigma2 = iv_long
    T1 = dte_short / 365.0
    T2 = dte_long / 365.0
    if T2 <= T1:
        return None

    numerator = (sigma2**2 * T2) - (sigma1**2 * T1)
    denominator = T2 - T1
    if denominator <= 0 or numerator < 0:
        return None

    forward_variance = numerator / denominator
    sigma_fwd = math.sqrt(forward_variance)
    ff = (sigma1 - sigma_fwd) / sigma_fwd
    return ff * 100

# ────────────────────────────────────────────────
#  GUI
# ────────────────────────────────────────────────

root = tk.Tk()
root.title("Tasty Forward Factor Scanner")
root.geometry("700x700")
root.resizable(True, True)

# ── Top frame ──
top_frame = tk.Frame(root)
top_frame.pack(pady=10, padx=10, fill="x")

tk.Label(top_frame, text="CSV File with tickers:").grid(row=0, column=0, padx=5, sticky="e")
file_path_var = tk.StringVar()
tk.Entry(top_frame, textvariable=file_path_var, width=50, state="readonly").grid(row=0, column=1, padx=5)
browse_btn = tk.Button(top_frame, text="Browse CSV")
browse_btn.grid(row=0, column=2, padx=5)

tk.Label(top_frame, text="Short Expiration (from SPY):").grid(row=1, column=0, padx=5, pady=5, sticky="e")
short_date_var = tk.StringVar()
short_combo = ttk.Combobox(top_frame, textvariable=short_date_var, state="readonly", width=20)
short_combo.grid(row=1, column=1, sticky="w", padx=5)

tk.Label(top_frame, text="Long Expiration (from SPY):").grid(row=2, column=0, padx=5, pady=5, sticky="e")
long_date_var = tk.StringVar()
long_combo = ttk.Combobox(top_frame, textvariable=long_date_var, state="readonly", width=20)
long_combo.grid(row=2, column=1, sticky="w", padx=5)

filter_var = tk.BooleanVar(value=False)
tk.Checkbutton(top_frame, text="Only show Forward Factor > 20%", variable=filter_var).grid(row=3, column=0, columnspan=3, sticky="w", pady=5)

button_frame = tk.Frame(top_frame)
button_frame.grid(row=4, column=0, columnspan=3, pady=10, sticky="ew")

run_btn = tk.Button(button_frame, text="Run Scan", bg="#4CAF50", fg="white", font=("Arial", 11, "bold"))
run_btn.pack(side="left", padx=10)

save_btn = tk.Button(button_frame, text="Save Results to CSV", bg="#2196F3", fg="white", state="disabled")
save_btn.pack(side="left", padx=10)

status_label = tk.Label(root, text="Ready", bd=1, relief="sunken", anchor="w")
status_label.pack(side="bottom", fill="x")

# ── Table frame ──
table_frame = tk.Frame(root)
table_frame.pack(fill="both", expand=True, padx=10, pady=5)

tree = ttk.Treeview(table_frame, show="headings")
tree.pack(fill="both", expand=True)

scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
scrollbar.pack(side="right", fill="y")
tree.configure(yscrollcommand=scrollbar.set)

tree.tag_configure("red", foreground="red")

current_results = []

# ── Functions ──

def browse_csv():
    path = filedialog.askopenfilename(
        title="Select CSV file",
        filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
    )
    if path:
        file_path_var.set(path)

def clear_table():
    for item in tree.get_children():
        tree.delete(item)
    for col in tree["columns"]:
        tree.heading(col, text="")
    tree["columns"] = ()

def populate_expiration_dropdowns():
    status_label.config(text="Fetching SPY expirations...", fg="blue")
    root.update()

    expirations = get_expirations_for_spy()

    if not expirations:
        messagebox.showwarning("Warning", "Could not fetch expiration dates from SPY.")
        status_label.config(text="Ready", fg="black")
        short_combo['values'] = []
        long_combo['values'] = []
        return

    # Convert string dates to aware datetime objects for accurate comparison
    today = datetime.now(timezone.utc)
    exp_datetimes = [datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=timezone.utc) for date in expirations]

    short_combo['values'] = expirations
    long_combo['values'] = expirations

    # Auto-select closest to 30 and 60 days
    target_short = today + timedelta(days=30)
    target_long = today + timedelta(days=60)

    # Find index closest to target
    short_idx = min(range(len(exp_datetimes)), key=lambda i: abs(exp_datetimes[i] - target_short).days)
    long_idx = min(range(len(exp_datetimes)), key=lambda i: abs(exp_datetimes[i] - target_long).days)

    short_combo.current(short_idx)
    long_combo.current(long_idx)

    status_label.config(text="Ready", fg="black")

def run_scan():
    global current_results
    status_label.config(text="Scanning...", fg="blue")
    root.update()

    clear_table()

    csv_path = file_path_var.get()
    if not csv_path or not os.path.exists(csv_path):
        messagebox.showerror("Error", "Please select a valid CSV file first.")
        status_label.config(text="Ready", fg="black")
        return

    short_date = short_date_var.get().strip()
    long_date = long_date_var.get().strip()
    if not short_date or not long_date:
        messagebox.showerror("Error", "Short and Long expiration dates are required.")
        status_label.config(text="Ready", fg="black")
        return

    dte_short = calculate_dte(short_date)
    dte_long = calculate_dte(long_date)
    if dte_short <= 0 or dte_long <= 0 or dte_short >= dte_long:
        messagebox.showerror("Error", "Invalid expiration dates (must be future dates, short before long).")
        status_label.config(text="Ready", fg="black")
        return

    tickers = []
    with open(csv_path, newline='') as f:
        reader = csv.reader(f)
        try:
            next(reader)
        except StopIteration:
            pass
        for row in reader:
            if row and row[0].strip():
                tickers.append(row[0].strip().upper())

    if not tickers:
        messagebox.showwarning("Warning", "No tickers found in CSV.")
        status_label.config(text="Ready", fg="black")
        return

    status_label.config(text=f"Fetching data for {len(tickers)} symbols...", fg="blue")
    root.update()

    try:
        metrics = get_market_metrics(tickers)
    except Exception as e:
        messagebox.showerror("API Error", str(e))
        status_label.config(text="Error — check credentials", fg="red")
        return

    results = []
    for row in metrics:
        symbol = row.get("symbol")
        if not symbol:
            continue

        expirations_raw = row.get("option-expiration-implied-volatilities", [])
        if not expirations_raw:
            continue

        # Check if this symbol has both selected dates
        has_short = any(exp["expiration-date"].startswith(short_date) for exp in expirations_raw)
        has_long = any(exp["expiration-date"].startswith(long_date) for exp in expirations_raw)
        if not (has_short and has_long):
            continue  # Skip symbols that don't match the selected SPY-based dates

        exp_list = []
        for exp in expirations_raw:
            dte = calculate_dte(exp["expiration-date"])
            if dte > 0:
                iv_str = exp.get("implied-volatility")
                if iv_str:
                    try:
                        exp_list.append({
                            "dte": dte,
                            "iv": float(iv_str),
                            "exp_date": exp["expiration-date"]
                        })
                    except:
                        pass

        if len(exp_list) < 2:
            continue

        # Use exact selected dates (no interpolation needed)
        iv_short = None
        iv_long = None
        for exp in exp_list:
            if exp["exp_date"].startswith(short_date):
                iv_short = exp["iv"]
            if exp["exp_date"].startswith(long_date):
                iv_long = exp["iv"]

        ff_pct = compute_forward_factor(
            iv_short, iv_long,
            dte_short=dte_short,
            dte_long=dte_long
        )

        if ff_pct is not None:
            h_short = f"IV {short_date} (~{dte_short} DTE)"
            h_long = f"IV {long_date} (~{dte_long} DTE)"

            results.append({
                "Symbol": symbol,
                h_short: f"{iv_short*100:.2f}%" if iv_short else "N/A",
                h_long: f"{iv_long*100:.2f}%" if iv_long else "N/A",
                "Forward Factor": ff_pct,
                "FF_display": f"{ff_pct:.2f}%"
            })

    # Sort descending by Forward Factor
    results.sort(key=lambda x: x["Forward Factor"], reverse=True)

    # Apply filter if checked
    if filter_var.get():
        results = [r for r in results if r["Forward Factor"] > 20]

    current_results = results

    if not results:
        status_label.config(text="No valid results found (or no matching expirations)", fg="orange")
        save_btn.config(state="disabled")
        return

    # Build columns
    columns = ["Symbol", h_short, h_long, "Forward Factor"]
    tree["columns"] = columns

    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, width=150, anchor="center")

    # Insert rows with conditional coloring
    for res in results:
        values = [res.get(col, "N/A") for col in columns]
        values[-1] = res["FF_display"]
        tags = ("red",) if res["Forward Factor"] > 20 else ()
        tree.insert("", "end", values=values, tags=tags)

    status_label.config(text=f"Scan complete — {len(results)} symbols (sorted by FF descending)", fg="green")
    save_btn.config(state="normal")

def save_to_csv():
    if not current_results:
        messagebox.showinfo("No Data", "No results to save yet.")
        return

    file_path = filedialog.asksaveasfilename(
        defaultextension=".csv",
        filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        title="Save Results As"
    )
    if not file_path:
        return

    columns = tree["columns"]

    with open(file_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(columns)
        for item in tree.get_children():
            row = tree.item(item)['values']
            writer.writerow(row)

    messagebox.showinfo("Saved", f"Results saved to:\n{file_path}")

# ── Bind buttons ──
browse_btn.config(command=browse_csv)
run_btn.config(command=run_scan)
save_btn.config(command=save_to_csv)

# Populate SPY expirations on startup
populate_expiration_dropdowns()

root.mainloop()