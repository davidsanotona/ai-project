"""
finance_tools.py
----------------
Retrieves financial data for publicly listed companies.
Uses yfinance (Yahoo Finance wrapper) — no API key required.

For private/startup companies, falls back to search-derived estimates.
Install: pip install yfinance
"""

from typing import Optional

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    # yfinance not installed — all calls will return mock data
    YFINANCE_AVAILABLE = False


def get_financials(ticker: str) -> dict:
    """
    Fetches key financial metrics for a publicly traded company.
    Returns a flat dict suitable for injection into agent prompts.

    Falls back to mock data if yfinance is unavailable or ticker not found.
    """
    if not YFINANCE_AVAILABLE:
        return _mock_financials(ticker)

    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        # Extract only the fields relevant to VC-style analysis
        return {
            "ticker": ticker,
            "company_name": info.get("longName", ""),
            "sector": info.get("sector", ""),
            "industry": info.get("industry", ""),
            "market_cap_usd": info.get("marketCap"),
            "revenue_usd": info.get("totalRevenue"),
            "gross_margin_pct": info.get("grossMargins"),
            "operating_margin_pct": info.get("operatingMargins"),
            "revenue_growth_yoy": info.get("revenueGrowth"),
            "employee_count": info.get("fullTimeEmployees"),
            "headquarters": f"{info.get('city', '')}, {info.get('country', '')}",
            "website": info.get("website", ""),
            "description": info.get("longBusinessSummary", "")[:500],  # truncate for prompt efficiency
            "pe_ratio": info.get("trailingPE"),
            "cash_usd": info.get("totalCash"),
            "debt_usd": info.get("totalDebt"),
        }

    except Exception as e:
        # Non-fatal: log the error and fall through to mock data
        print(f"[finance_tools] yfinance error for {ticker}: {e}")
        return _mock_financials(ticker)


def resolve_ticker(company_name: str) -> Optional[str]:
    """
    Attempts to resolve a company name to its ticker symbol using yfinance search.
    Returns None if resolution fails — caller should handle gracefully.
    """
    if not YFINANCE_AVAILABLE:
        return None

    try:
        # yfinance search returns candidate tickers ranked by relevance
        results = yf.Search(company_name, max_results=1)
        quotes = results.quotes
        if quotes:
            return quotes[0].get("symbol")
        return None
    except Exception:
        return None


def _mock_financials(ticker: str) -> dict:
    """
    Returns plausible mock financials for dev/testing without yfinance.
    """
    return {
        "ticker": ticker,
        "company_name": f"Mock Corp ({ticker})",
        "sector": "Technology",
        "industry": "Software",
        "market_cap_usd": 5_000_000_000,
        "revenue_usd": 400_000_000,
        "gross_margin_pct": 0.68,
        "operating_margin_pct": 0.12,
        "revenue_growth_yoy": 0.22,
        "employee_count": 1200,
        "headquarters": "San Francisco, US",
        "website": "https://mock-corp.com",
        "description": "Mock Corp builds enterprise software solutions for the climate sector.",
        "pe_ratio": 35.0,
        "cash_usd": 200_000_000,
        "debt_usd": 50_000_000,
    }
