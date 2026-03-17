<!-- .github/copilot-instructions.md - guidance for AI coding agents working on this repo -->
# Tasty Forward Factor Scanner — AI assistant instructions

This repository contains two primary scripts: `tasty_ff_gui.py` (Tkinter desktop GUI) and
`tasty_ff_scanner.py` (command-line scanner). The project reads tickers from `tickers.csv`,
loads OAuth credentials from a `.env` file, queries tastytrade endpoints, computes a
variance-weighted forward volatility and a Forward Factor, and presents results.

Key architecture and data flow
- **Input**: `tickers.csv` (one symbol per line). GUI lets user choose CSV via file dialog.
- **Credentials**: `.env` with `TASTY_CLIENT_ID`, `TASTY_CLIENT_SECRET`, `TASTY_REFRESH_TOKEN`, optional `TASTY_BASE_URL`.
- **HTTP layer**: `TastySession` in both scripts handles OAuth refresh and exposes `get_headers()`.
- **API endpoints**: `/market-metrics?symbols=...` (main data source) and `/option-chains/{SYMBOL}/nested`
  (used to fetch SPY expirations for the GUI dropdowns).
- **Computation**: `compute_forward_factor` implements the math from README:
  σ_fwd = sqrt((σ₂²·T₂ - σ₁²·T₁)/(T₂ - T₁)); FF = (σ₁ - σ_fwd)/σ_fwd (expressed as percent).

Project-specific conventions and patterns
- Implied vol values from the API are decimals (e.g. 0.25 = 25%); UI/CLI multiply by 100 for display.
- The GUI uses SPY expirations as canonical short/long dates; symbols without those exact dates are skipped.
- Date handling is timezone-aware; `calculate_dte` returns integer days until expiration.
- Linear interpolation between adjacent expirations is used when exact DTEs aren't present (`interpolate_iv_with_dte`).
- Forward Factor > 20% is a project convention (highlight red in GUI, optional filter checkbox).

Developer workflows & commands
- Install dependencies: `python -m pip install --upgrade pip && python -m pip install requests python-dotenv`
- CLI scanner needs `tabulate`: `python -m pip install tabulate`
- Run GUI: `python tasty_ff_gui.py` (macOS/Linux may require `python3`).
- Run CLI scanner: `python tasty_ff_scanner.py`.
- Ensure `.env` present before running; missing credentials raise ValueError on startup.

What to watch for when editing code
- Preserve `TastySession` semantics: always refresh before sending requests; token expiry is tracked in seconds.
- Keep date parsing consistent: functions accept ISO-like strings and detect `T`/`Z` forms.
- Default edit policy: prefer minimal, focused `apply_patch` edits that change only the necessary lines; full file refactors
  require explicit request.
- Avoid changing the dynamic column header pattern used in both scripts; headers include the actual expiration date.
- Network errors: GUI surfaces API errors via messagebox and sets status label; CLI prints and exits. Follow existing UX.

Files to inspect for examples
- `tasty_ff_gui.py` — full GUI flow (dropdowns, CSV reading, table population).
- `tasty_ff_scanner.py` — headless/CLI implementation, interpolation example, and `tabulate` output.
- `README.md` — user-facing math, install/run docs, and environment setup.

If something is ambiguous or you need more context, ask for the preferred UX (e.g. how to handle interpolation fallbacks,
or whether to add retries/backoff for HTTP). Include short code snippets that follow the existing `TastySession` pattern.

End of file.
