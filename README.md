# Tastytrade Forward Factor Scanner GUI

A simple desktop GUI application that connects to the **tastytrade Open API** to scan stocks/ETFs for **variance-weighted Forward Factor** (forward implied volatility) and displays results in a sortable table.

- Results sorted by Forward Factor descending  
- Forward Factor > 20% highlighted in **red**  
- Load tickers from a CSV file (one symbol per line)  
- Adjustable short & long DTE (default: 30 and 60 days)  
- Uses tastytrade `/market-metrics` endpoint  
- Dynamic column headers with actual expiration dates

## Features

- Tkinter-based GUI (no browser/server needed)  
- Variance-weighted forward vol calculation:  
  σ_fwd = √[(σ₂²·T₂ - σ₁²·T₁) / (T₂ - T₁)]  
  FF = (σ₁ - σ_fwd) / σ_fwd  
- Scrollable table with colored results  
- Beginner-friendly setup instructions

## Requirements

- Python 3.8+  
- tastytrade account with OAuth credentials (Client ID, Client Secret, Refresh Token)  
- Windows, macOS, or Linux

## Installation & Setup (for complete beginners)

1. **Install Python** (skip if you already have it)

   - Go to: https://www.python.org/downloads/
   - Download the latest **Python 3.x** version
   - Run the installer
   - **Very important**: check the box **“Add python.exe to PATH”** (near the bottom)
   - Click **Install Now**
   - After it finishes, restart your computer (recommended)

   Verify:
   - Windows: open Command Prompt → type `python --version` → should show Python 3.x
   - macOS: open Terminal → type `python3 --version`

2. **Create a project folder**

   - On your Desktop (or Documents), right-click → **New** → **Folder**
   - Name it `TastyScanner` (or any name you prefer)

3. **Save the program file**

   - Open Notepad (Windows) or TextEdit (macOS)
   - Copy the entire code from the **tasty_ff_gui.py** section below
   - Paste it into the editor
   - **File → Save As…**
   - Navigate to your `TastyScanner` folder
   - File name: `tasty_ff_gui.py` (must end with `.py`)
   - Save as type: **All Files** (not Text Document)
   - Click Save

4. **Create the `.env` file with your tastytrade API credentials**

   - In the same folder, right-click → **New** → **Text Document**
   - Name it exactly: `.env` (starts with a dot)
     - Windows may warn about removing `.txt` — click Yes
   - Open it with Notepad/TextEdit
   - Paste these lines:

```    
TASTY_CLIENT_ID=your_client_id_here
TASTY_CLIENT_SECRET=your_client_secret_here
TASTY_REFRESH_TOKEN=your_refresh_token_here
TASTY_BASE_URL=https://api.tastytrade.com
```

- Replace the placeholder values with your real ones

**How to get the credentials**:
1. Log in to https://my.tastytrade.com
2. Go to **Account** → **API Access** → **OAuth Applications**
3. Click **Create New Application** (or similar button)
4. Give it a name (e.g. "FF Scanner")
5. Select scopes: at least **read** (add **trade** if needed later)
6. Save/create the app → you’ll see **Client ID** and **Client Secret**
7. Click **Create Grant** / **Generate Personal Grant** → copy the **Refresh Token** (long string)
8. Paste all three values into your `.env` file
9. Save and close

5. **Install the required libraries**

- Open **Command Prompt** (Windows: Windows key + S → type `cmd`) or **Terminal** (macOS)
- Navigate to your folder:

`cd Desktop\TastyScanner`
(macOS/Linux: cd ~/Desktop/TastyScanner)

* Run these commands one by one: 
`python -m pip install --upgrade pip`
`python -m pip install requests python-dotenv` 
(on macOS/Linux you may need python3 instead of python)


* Create a sample CSV file with tickers
In the same folder, create a new text file → name it tickers.csv
Open it and add one ticker per line (no header needed):
```
TSLA
AAPL
NVDA
SPY
USO
QQQ
```

Save it

## Run the program
In the same Command Prompt/Terminal window, type:Bash

```
python tasty_ff_gui.py(macOS/Linux: python3 tasty_ff_gui.py)
```
Press Enter → the GUI window should open!


## How to Use

1. Click Browse CSV → select your tickers.csv
1. Set Short DTE and Long DTE (defaults: 30 and 60)
1. Click Run Scan
1. Wait a few seconds → results appear in the table
1. Sorted by Forward Factor descending
1. Forward Factor > 20% appears in red


## Troubleshooting

### python is not recognized
Reinstall Python and make sure “Add to PATH” was checked. Restart computer.

### 401/403 Unauthorized
Double-check .env values. Refresh token may have expired — regenerate in tastytrade OAuth settings.

### No results in table
* Verify CSV has valid tickers
* Try different DTE values
* Ensure symbols have options data

### Window size issues
Edit this line in the code:

```python
Pythonroot.geometry("1100x700")
# Try "1200x800" or "1400x900" for better fit.
```

### License
MIT License (or choose your own)
Questions or improvements?
→ Open an issue on GitHub
→ Or reach out on X: @itnetworkguru

Happy scanning!
