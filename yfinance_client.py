"""Small helper module to fetch next earnings dates using yfinance.

Usage:
    from yfinance_client import YFinanceClient, read_tickers_from_csv

    client = YFinanceClient()
    tickers = read_tickers_from_csv("tickers.csv")
    dates = client.fetch_next_earnings_for(tickers)

The methods return ISO date strings (YYYY-MM-DD) or None when unknown.
"""
from typing import List, Dict, Optional
import csv
from datetime import datetime, timezone

import yfinance as yf


class YFinanceClient:
    def __init__(self):
        pass

    def _to_iso(self, val) -> Optional[str]:
        if val is None:
            return None
        # pandas Timestamp or datetime
        try:
            return val.date().isoformat()
        except Exception:
            pass

        # numeric unix timestamp
        try:
            ts = int(val)
            return datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat()
        except Exception:
            pass

        # fallback to string parsing (take YYYY-MM-DD prefix)
        try:
            s = str(val)
            return s.split("T")[0]
        except Exception:
            return None

    def get_next_earnings(self, symbol: str) -> Optional[str]:
        """Return next earnings date for `symbol` as ISO YYYY-MM-DD or None."""
        try:
            t = yf.Ticker(symbol)

            # Try common info keys first
            info = getattr(t, "info", {}) or {}
            for k in ("nextEarningsDate", "earningsDate", "next_earnings_date"):
                if k in info and info[k]:
                    iso = self._to_iso(info[k])
                    if iso:
                        return iso

            # Prefer the ticker.calendar value when available (contains 'Earnings Date')
            try:
                cal = getattr(t, "calendar", None)
                if cal is not None:
                    # Try common key access; cal may be a pandas DataFrame or dict-like
                    ed_val = None
                    try:
                        if hasattr(cal, 'get'):
                            ed_val = cal.get('Earnings Date')
                    except Exception:
                        ed_val = None

                    if ed_val is None:
                        try:
                            ed_val = cal['Earnings Date']
                        except Exception:
                            ed_val = None

                    if ed_val is not None:
                        # ed_val may be a pandas Series/Index/Timestamp or sequence; take first element
                        try:
                            first = ed_val.iloc[0] if hasattr(ed_val, 'iloc') else (ed_val[0] if isinstance(ed_val, (list, tuple)) else ed_val)
                        except Exception:
                            first = ed_val
                        iso = self._to_iso(first)
                        if iso:
                            return iso
            except Exception:
                pass

            # Try the newer helper that returns a DataFrame (yfinance >= 0.2.x)
            try:
                ed = t.get_earnings_dates(limit=1)
                if ed is not None and len(ed) > 0:
                    # ed may be a pandas DataFrame; try index or common columns
                    try:
                        # index may contain the datetime
                        idx = ed.index[0]
                        iso = self._to_iso(idx)
                        if iso:
                            return iso
                    except Exception:
                        pass

                    try:
                        row = ed.iloc[0]
                        for col in ("Earnings Date", "startdatetime", "startdatetimeUTC"):
                            if col in row and row[col] is not None:
                                iso = self._to_iso(row[col])
                                if iso:
                                    return iso
                    except Exception:
                        pass
            except Exception:
                # ignore yfinance internal failures and fall back
                pass
        except Exception:
            return None

        return None

    def fetch_next_earnings_for(self, symbols: List[str]) -> Dict[str, Optional[str]]:
        results: Dict[str, Optional[str]] = {}
        for s in symbols:
            results[s] = self.get_next_earnings(s)
        return results


def read_tickers_from_csv(path: str) -> List[str]:
    tickers: List[str] = []
    with open(path, newline="") as f:
        reader = csv.reader(f)
        # Detect and skip a header row if it looks like one (e.g. "symbol", "ticker")
        first = next(reader, None)
        def _is_header(cell: str) -> bool:
            if not cell:
                return False
            c = cell.strip()
            low = c.lower()
            if low in ("symbol", "ticker", "tickers"):
                return True
            # If cell contains letters but is not all-uppercase ticker-like (e.g. "Symbol", "Ticker")
            if any(ch.isalpha() for ch in c) and not c.replace('.', '').isupper():
                return True
            # Unusually long first cell likely a header
            if len(c) > 6:
                return True
            return False

        if first and first[0].strip():
            first_cell = first[0].strip()
            if not _is_header(first_cell):
                tickers.append(first_cell.upper())

        for row in reader:
            if row and row[0].strip():
                tickers.append(row[0].strip().upper())
    return tickers
