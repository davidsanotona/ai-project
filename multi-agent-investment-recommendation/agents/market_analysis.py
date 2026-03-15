"""
market_analysis.py
------------------
Market & Competitor Agent — runs in parallel with ESG agent.

Responsibilities:
- Estimate Total Addressable Market (TAM) with growth rate
- Identify top competitors and differentiation factors
- Assess competitive moat (network effects, IP, switching costs, brand)

Outputs: populates state.market (MarketProfile dataclass)
"""

import json
import os
from models.state import DealState, MarketProfile
from tools.search_tools import tavily_search

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = "claude-sonnet-4-20250514"
ANTHROPIC_ENDPOINT = "https://api.anthropic.com/v1/messages"


def run(state: DealState) -> DealState:
    """
    Entry point called by the Orchestrator.
    Runs in parallel with esg_climate agent.
    """
    company = state.company_name
    sector = state.intel.business_model

    search_text = _gather_market_data(company, sector)
    market_dict = _analyze_market_with_claude(company, sector, search_text)

    state.market = _hydrate_market(market_dict)
    return state


def _gather_market_data(company: str, sector: str) -> str:
    queries = [
        f"{company} total addressable market TAM size 2024 2025",
        f"{company} competitors landscape competitive analysis",
        f"{sector} market growth forecast CAGR",
        f"{company} competitive advantage moat differentiation",
    ]

    combined = []
    for q in queries:
        result = tavily_search(q, max_results=3)
        if result.get("answer"):
            combined.append(result["answer"])
        for r in result.get("results", []):
            combined.append(r.get("content", ""))

    return "\n\n".join(combined)


def _analyze_market_with_claude(company: str, sector: str, search_text: str) -> dict:
    import urllib.request

    prompt = f"""You are a market analyst at a VC fund.

Analyze the market position of {company} (sector: {sector or 'unknown'}).

Market Research Data:
{search_text}

Return ONLY valid JSON:
{{
  "tam_usd": float or null,
  "sector": "primary sector label",
  "growth_rate_pct": float or null,
  "competitors": ["competitor1", "competitor2", "competitor3"],
  "competitive_moat": "description of competitive advantage or 'unclear'",
  "market_summary": "2-3 sentence analyst summary of market opportunity"
}}

For tam_usd and growth_rate_pct: use the most credible figure from the data.
If no TAM figure is found, estimate conservatively based on sector context.
Return only JSON."""

    payload = json.dumps({
        "model": CLAUDE_MODEL,
        "max_tokens": 800,
        "messages": [{"role": "user", "content": prompt}]
    }).encode("utf-8")

    req = urllib.request.Request(
        ANTHROPIC_ENDPOINT,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            raw_text = data["content"][0]["text"].strip()
            raw_text = raw_text.replace("```json", "").replace("```", "").strip()
            return json.loads(raw_text)
    except Exception as e:
        print(f"[market_analysis] failed: {e}")
        return {}


def _hydrate_market(market_dict: dict) -> MarketProfile:
    return MarketProfile(
        tam_usd=market_dict.get("tam_usd"),
        sector=market_dict.get("sector", ""),
        growth_rate_pct=market_dict.get("growth_rate_pct"),
        competitors=market_dict.get("competitors", []),
        competitive_moat=market_dict.get("competitive_moat", ""),
        market_summary=market_dict.get("market_summary", ""),
    )
