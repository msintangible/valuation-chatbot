"""
query_classifier.py
--------------------
Mandatory input-classification layer for the Financial Intelligence Agent.

PROBLEM THIS FIXES
-------------------
The agent used to extract "tickers" with a single regex (`\\b[A-Z]{1,5}\\b`)
applied directly to the raw query, with no concept of "this token is a
financial metric, not a company". Financial abbreviations such as ROE, ROA,
EPS, and PE are 1-5 uppercase letters, so they matched the same shape as a
real ticker and were sent straight to the valuation pipeline:

    "What does ROE tell me?" -> tickers=["ROE"] -> POST /predict/ {"ticker": "ROE"}
    -> 404 from yfinance -> empty/broken response shown to the user.

THE FIX
-------
Before any tool/API call is even considered, `classify_query()` puts every
input into exactly one of four buckets (TICKER_QUERY, METRIC_EXPLANATION,
MIXED_QUERY, GENERAL_QUESTION). Financial metrics are recognised and
excluded from ticker extraction *before* the ticker regex ever runs, not
after — so a metric token can never reach a ticker lookup API.

Ticker candidates that survive the metric/stopword exclusion are then
checked against a curated, deterministic `KNOWN_TICKER_UNIVERSE`. This is
intentionally a fast, local, zero-network check — classification must be
deterministic and instantaneous, never dependent on a live API response.
The universe is necessarily incomplete (thousands of real tickers exist
that aren't in it), so a candidate NOT in the universe is marked
"unverified" rather than auto-rejected: it's still eligible to be checked
by the backend's live yfinance-backed `validate_ticker()` later in the
pipeline, which remains the final source of truth. What classification
guarantees is narrower but load-bearing: a candidate that IS a known
metric or stopword is *never* treated as a ticker, full stop.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List


# ─────────────────────────────────────────────────────────────────────────
# Category constants
# ─────────────────────────────────────────────────────────────────────────


class QueryCategory:
    TICKER_QUERY = "TICKER_QUERY"
    METRIC_EXPLANATION = "METRIC_EXPLANATION"
    MIXED_QUERY = "MIXED_QUERY"
    GENERAL_QUESTION = "GENERAL_QUESTION"


# ─────────────────────────────────────────────────────────────────────────
# Metric lexicon — every abbreviation/phrase here is NEVER a ticker.
# Checked before the ticker regex is given a chance to misclassify it.
# ─────────────────────────────────────────────────────────────────────────

METRIC_LEXICON: dict[str, str] = {
    "ROE": "Return on Equity",
    "ROA": "Return on Assets",
    "ROI": "Return on Investment",
    "ROIC": "Return on Invested Capital",
    "EPS": "Earnings Per Share",
    "PE": "Price-to-Earnings Ratio",
    "PEG": "Price/Earnings-to-Growth Ratio",
    "EBITDA": "Earnings Before Interest, Taxes, Depreciation & Amortization",
    "EBIT": "Earnings Before Interest and Taxes",
    "RSI": "Relative Strength Index",
    "MACD": "Moving Average Convergence Divergence",
    "PB": "Price-to-Book Ratio",
    "PS": "Price-to-Sales Ratio",
    "DE": "Debt-to-Equity Ratio",
    "FCF": "Free Cash Flow",
    "CAGR": "Compound Annual Growth Rate",
    "YOY": "Year-over-Year Growth",
    "WACC": "Weighted Average Cost of Capital",
    "BETA": "Beta (volatility relative to the market)",
    "APR": "Annual Percentage Rate",
    "APY": "Annual Percentage Yield",
    "NAV": "Net Asset Value",
    "AUM": "Assets Under Management",
}

# Multi-word / slash-containing metric phrases — substring-matched against
# the lowercased query since they can't be caught by a single-token regex.
METRIC_PHRASES: List[str] = [
    "p/e", "p/b", "p/s", "d/e",
    "debt to equity", "debt-to-equity",
    "current ratio", "quick ratio",
    "gross margin", "operating margin", "net margin", "profit margin",
    "free cash flow", "book value", "price to book", "price to sales",
    "price to earnings", "price-to-earnings", "dividend yield",
    "interest coverage", "return on equity", "return on assets",
    "return on investment", "return on invested capital",
    "earnings per share", "moving average", "market cap", "market capitalization",
]

# Common English words that happen to be 1-5 uppercase letters once the
# query is scanned — must never be mistaken for a ticker.
TICKER_STOPWORDS: set[str] = {
    "A", "I", "TO", "OF", "ON", "IS", "DO", "BE", "IT", "OR", "AS", "AT",
    "MY", "ME", "SO", "IF", "AN", "AM", "BY", "GO", "NO", "UP", "US",
    "HOW", "WHAT", "WHY", "WHEN", "WHERE", "WHO", "CAN", "SHOULD", "COULD",
    "WOULD", "WILL", "WITH", "FOR", "AND", "THE", "ARE", "THIS", "THAT",
    "TELL", "ABOUT", "DOES", "MEAN", "GOOD", "BAD", "YOU", "YOUR", "ALL",
    "NOW", "GET", "SEE", "WAY", "OUT", "ITS", "OUR", "HAS", "HAD", "NOT",
    "BUY", "SELL", "HOLD", "HIGH", "LOW", "NEW", "TOP", "BEST", "WORST",
}

# ─────────────────────────────────────────────────────────────────────────
# Known ticker universe — deterministic fast-path allow-list spanning the
# model's 8 trained sectors plus other widely-discussed symbols. NOT
# exhaustive by design (see module docstring): a candidate missing from
# this set is "unverified", not "invalid" — it still goes through the
# backend's live validate_ticker() check before any classification of
# "Invalid ticker" is shown to the user.
# ─────────────────────────────────────────────────────────────────────────

KNOWN_TICKER_UNIVERSE: set[str] = {
    # Technology
    "AAPL", "MSFT", "GOOGL", "GOOG", "META", "NVDA", "AMD", "INTC", "CRM",
    "ORCL", "ADBE", "CSCO", "IBM", "AVGO", "QCOM", "TXN", "NOW", "INTU",
    "AMAT", "MU", "PLTR", "SNAP", "UBER", "LYFT", "SQ", "SHOP", "SPOT",
    "ABNB", "NFLX", "DIS", "T", "VZ", "TMUS",
    # Financials
    "JPM", "BAC", "WFC", "C", "GS", "MS", "V", "MA", "AXP", "SCHW", "BLK",
    "SOFI", "PYPL", "COF", "USB", "PNC", "TFC", "COIN",
    # Healthcare
    "UNH", "JNJ", "PFE", "LLY", "ABBV", "MRK", "TMO", "ABT", "DHR", "BMY",
    "AMGN", "GILD", "CVS", "MDT", "ISRG",
    # Discretionary
    "AMZN", "TSLA", "HD", "NKE", "MCD", "SBUX", "LOW", "TGT", "BKNG",
    "CMG", "ROST", "TJX", "F", "GM", "RIVN", "LCID", "GME", "AMC",
    # Energy
    "XOM", "CVX", "COP", "SLB", "EOG", "OXY", "PSX", "VLO", "MPC",
    # Staples
    "PG", "KO", "PEP", "WMT", "COST", "MDLZ", "CL", "KMB", "GIS", "KHC",
    # Industrials
    "CAT", "HON", "GE", "BA", "UPS", "LMT", "RTX", "DE", "MMM", "UNP", "EMR",
    # Utilities
    "NEE", "DUK", "SO", "D", "AEP", "EXC", "SRE", "XEL", "ED",
}


@dataclass
class QueryClassification:
    """Result of classify_query() — the mandatory first step for every
    incoming query, before any tool/API call is considered."""

    category: str
    raw_query: str
    ticker_candidates: List[str] = field(default_factory=list)
    recognized_tickers: List[str] = field(default_factory=list)
    unverified_tickers: List[str] = field(default_factory=list)
    metrics: List[str] = field(default_factory=list)

    @property
    def has_tickers(self) -> bool:
        return bool(self.ticker_candidates)

    @property
    def has_metrics(self) -> bool:
        return bool(self.metrics)


def extract_metric_terms(query: str) -> List[str]:
    """Find financial-metric terms/phrases in the query. Order-preserving,
    de-duplicated. These must never be passed to a ticker lookup API."""
    found: List[str] = []
    seen: set[str] = set()
    normalized = query.lower()

    for phrase in METRIC_PHRASES:
        if phrase in normalized and phrase not in seen:
            seen.add(phrase)
            found.append(phrase)

    for token in re.findall(r"[A-Za-z]{1,6}", query):
        upper = token.upper()
        if upper in METRIC_LEXICON and upper not in seen:
            seen.add(upper)
            found.append(upper)

    return found


def _strip_metric_phrases(query: str) -> str:
    """Remove matched metric phrases from the text before ticker
    extraction runs. Without this, a punctuation-containing phrase like
    "P/E" gets split by `\\b` word boundaries into separate "P" and "E"
    tokens, which then pass the ticker shape check (single letters ARE
    valid real tickers — "F" is Ford, "T" is AT&T — so they can't be
    blanket-excluded). Stripping the whole phrase first means its
    sub-tokens are never seen by the ticker regex at all."""
    stripped = query
    for phrase in METRIC_PHRASES:
        stripped = re.sub(re.escape(phrase), " ", stripped, flags=re.IGNORECASE)
    return stripped


def extract_ticker_candidates(query: str) -> List[str]:
    """Structural ticker candidates: 1-5 consecutive uppercase letters,
    with known metric phrases stripped first, then known metric
    abbreviations and common stopwords excluded token-by-token, BEFORE
    anything is ever considered a ticker. Order-preserving, de-duplicated.

    This is the single source of truth for "does this token look like a
    ticker" — chatbot.py must not run its own competing regex.
    """
    candidates: List[str] = []
    seen: set[str] = set()
    for token in re.findall(r"\b[A-Z]{1,5}\b", _strip_metric_phrases(query)):
        if token in METRIC_LEXICON or token in TICKER_STOPWORDS:
            continue
        if token not in seen:
            seen.add(token)
            candidates.append(token)
    return candidates


def validate_against_universe(candidates: List[str]) -> tuple[List[str], List[str]]:
    """Split ticker candidates into (recognized, unverified) using the
    deterministic local universe. Does not make any network call."""
    recognized = [t for t in candidates if t in KNOWN_TICKER_UNIVERSE]
    unverified = [t for t in candidates if t not in KNOWN_TICKER_UNIVERSE]
    return recognized, unverified


def classify_query(query: str) -> QueryClassification:
    """MANDATORY FIRST STEP. Classify a raw user query into exactly one of:

      A. TICKER_QUERY        — only ticker-shaped tokens, no metric terms
      B. METRIC_EXPLANATION  — only financial-metric terms, no tickers
      C. MIXED_QUERY         — both tickers and metric terms present
      D. GENERAL_QUESTION    — neither (portfolio advice, greetings, etc.)

    No tool/API call should be made anywhere upstream of this function's
    result. Metric terms are extracted independently of, and prior to,
    ticker extraction, so a metric token can never leak into the ticker
    list (the original bug: "ROE" matching the ticker regex).
    """
    metrics = extract_metric_terms(query)
    ticker_candidates = extract_ticker_candidates(query)
    recognized, unverified = validate_against_universe(ticker_candidates)

    if ticker_candidates and metrics:
        category = QueryCategory.MIXED_QUERY
    elif ticker_candidates:
        category = QueryCategory.TICKER_QUERY
    elif metrics:
        category = QueryCategory.METRIC_EXPLANATION
    else:
        category = QueryCategory.GENERAL_QUESTION

    return QueryClassification(
        category=category,
        raw_query=query,
        ticker_candidates=ticker_candidates,
        recognized_tickers=recognized,
        unverified_tickers=unverified,
        metrics=metrics,
    )
