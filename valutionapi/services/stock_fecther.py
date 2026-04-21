"""
sector_fetcher.py
-----------------
Fetches live ticker lists by sector using multiple ETF holdings via yfinance.
Multiple ETFs per sector are merged to get more tickers than any single ETF returns.
"""

from __future__ import annotations
import yfinance as yf

# Multiple ETFs per sector — merged to maximise ticker coverage
# Each ETF tracks the same sector from a different angle / index
SECTOR_ETFS: dict[str, list[str]] = {
    "Technology": ["XLK"],
    "Financials": ["XLF"],
    "Healthcare": ["XLV"],
    "Discretionary": ["XLY"],
    "Energy": ["XLE"],
    "Staples": ["XLP"],
    "Industrials": ["XLI"],
    "Utilities": ["XLU"],
}

# Static fallback if all ETF fetches fail
SECTOR_FALLBACK: dict[str, list[str]] = {
    "Technology": ["AAPL", "MSFT", "NVDA", "ORCL", "ADBE", "CRM", "INTC", "CSCO", "AMD", "IBM"],
    "Financials": ["JPM", "BAC", "GS", "MS", "WFC", "C", "BLK", "PYPL", "V", "MA"],
    "Healthcare": ["PFE", "JNJ", "UNH", "ABBV", "MRK", "LLY", "AMGN", "TMO", "GILD", "BMY"],
    "Discretionary": ["TSLA", "AMZN", "F", "GM", "HD", "NKE", "SBUX", "MCD", "BKNG", "NCLH"],
    "Energy": ["XOM", "CVX", "COP", "SLB", "EOG", "MPC", "VLO", "PSX", "HAL", "OXY"],
    "Staples": ["WMT", "KO", "PEP", "COST", "PG", "CL", "MO", "TGT", "PM", "MDLZ"],
    "Industrials": ["BA", "CAT", "GE", "UPS", "FDX", "HON", "LMT", "MMM", "DE", "RTX"],
    "Utilities": ["NEE", "DUK", "SO", "D", "AEP", "EXC", "XEL", "WEC", "AWK", "DTE"],
}


def _get_etf_tickers(etf_symbol: str) -> list[str]:
    """
    Fetch holdings from a single ETF.
    Returns a list of ticker strings or empty list on failure.
    """
    try:
        etf = yf.Ticker(etf_symbol)
        holdings = etf.funds_data.top_holdings

        if holdings is None or holdings.empty:
            return []

        tickers = [str(t).upper() for t in holdings.index.tolist()]
        print(f"    {etf_symbol} -> {len(tickers)} tickers")
        return tickers

    except Exception as e:
        print(f"    {etf_symbol} -> failed ({e})")
        return []


def fetch_tickers_for_sector(
    sector_label: str,
    max_results: int = 40,
) -> list[str]:
    """
    Fetch tickers for a sector by merging holdings from multiple ETFs.
    Deduplicates across ETFs so each ticker only appears once.
    Falls back to static list if all ETFs fail.

    Args:
        sector_label: normalised training label e.g. "Financials"
        max_results:  max tickers to return after merging

    Returns:
        list of unique uppercase ticker strings
    """
    etf_list = SECTOR_ETFS.get(sector_label)
    if not etf_list:
        print(f"  [sector_fetcher] Unknown sector: '{sector_label}'")
        return SECTOR_FALLBACK.get(sector_label, [])[:max_results]

    print(f"  [sector_fetcher] Fetching {sector_label} from {etf_list}...")

    seen = set()
    merged = []

    for etf_symbol in etf_list:
        tickers = _get_etf_tickers(etf_symbol)
        for ticker in tickers:
            if ticker not in seen:
                seen.add(ticker)
                merged.append(ticker)

    if not merged:
        print(f"  [sector_fetcher] All ETFs failed for {sector_label} — using fallback")
        return SECTOR_FALLBACK.get(sector_label, [])[:max_results]

    result = merged[:max_results]
    print(f"  [sector_fetcher] {sector_label} -> {len(result)} unique tickers after merge")
    return result


def fetch_tickers_for_sectors(
    sector_labels: list[str],
    max_per_sector: int = 40,
) -> dict[str, list[str]]:
    """
    Fetch tickers for multiple sectors.
    Returns dict mapping sector_label -> list of tickers.
    """
    return {sector: fetch_tickers_for_sector(sector, max_results=max_per_sector) for sector in sector_labels}


if __name__ == "__main__":
    all_tickers = fetch_tickers_for_sectors(list(SECTOR_ETFS.keys()))
    for sector, tickers in all_tickers.items():
        print(f"\n{sector} ({len(tickers)} tickers):")
        print(tickers)
