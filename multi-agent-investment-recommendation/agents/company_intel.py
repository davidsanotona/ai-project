"""
company_intel.py
----------------
Company Intel Agent — first agent in the parallel execution phase.

Responsibilities:
- Resolve company identity (founding year, HQ, founders)
- Summarize business model and revenue strategy
- Pull funding history and key investors
- Optionally enrich with live financial data if company is public

Outputs: populates state.intel (CompanyIntel dataclass)
"""

import json
import os
from models.state import DealState, CompanyIntel
from tools.search_tools import tavily_search
from tools.finance_tools import get_financials, resolve_ticker

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = "claude-sonnet-4-20250514"
ANTHROPIC_ENDPOINT = "https://api.anthropic.com/v1/messages"


def run(state: DealState) -> DealState:
    """
    Entry point called by the Orchestrator.
    Fetches company data, calls Claude to structure it,
    and writes results into state.intel.
    """
    company = state.company_name

    # Step 1: Gather raw data from external sources in parallel conceptually,
    # but executed sequentially here for simplicity
    search_results = _gather_search_data(company)
    financial_data = _gather_financial_data(company)

    # Step 2: Ask Claude to extract structured intel from raw search data
    intel_dict = _extract_intel_with_claude(company, search_results, financial_data)

    # Step 3: Hydrate the CompanyIntel dataclass from Claude's structured output
    state.intel = _hydrate_intel(intel_dict, financial_data)

    return state


def _gather_search_data(company: str) -> str:
    """
    Runs multiple targeted searches and concatenates results into a single
    context string for Claude to reason over.
    """
    queries = [
        f"{company} company overview founding team history",
        f"{company} funding rounds investors Series",
        f"{company} business model revenue",
    ]

    combined = []
    for q in queries:
        result = tavily_search(q, max_results=3)
        # Use the synthesized Tavily answer if available, else fall back to snippets
        if result.get("answer"):
            combined.append(result["answer"])
        for r in result.get("results", []):
            combined.append(r.get("content", ""))

    return "\n\n".join(combined)


def _gather_financial_data(company: str) -> dict:
    """
    Attempts to enrich with structured financial data if the company is public.
    Returns empty dict for private companies — Claude handles the absence gracefully.
    """
    ticker = resolve_ticker(company)
    if ticker:
        return get_financials(ticker)
    return {}


def _extract_intel_with_claude(company: str, search_text: str, financials: dict) -> dict:
    """
    Calls Claude with the raw search data and asks it to return structured JSON.
    Using JSON-mode prompting: we instruct Claude to return only valid JSON,
    no markdown, no preamble — so we can parse it directly.
    """
    import urllib.request

    # Inject financial data into prompt only if available
    fin_section = f"\n\nFinancial data (if public):\n{json.dumps(financials, indent=2)}" if financials else ""

    prompt = f"""You are a VC research analyst. Extract structured company intelligence from the sources below.

Company: {company}

Search data:
{search_text}
{fin_section}

Return ONLY a valid JSON object with these exact keys:
{{
  "name": "full company name",
  "description": "2-3 sentence company overview",
  "founded_year": integer or null,
  "headquarters": "City, Country",
  "founders": ["name1", "name2"],
  "business_model": "brief description of how they make money",
  "funding_stage": "Seed / Series A / Series B / Public / etc.",
  "total_funding_usd": float or null,
  "key_investors": ["investor1", "investor2"],
  "revenue_usd": float or null,
  "employee_count": integer or null
}}

If a field is unknown, use null. Return only the JSON — no explanation."""

    payload = json.dumps({
        "model": CLAUDE_MODEL,
        "max_tokens": 1000,
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
            # Strip any accidental markdown code fences before parsing
            raw_text = raw_text.replace("```json", "").replace("```", "").strip()
            return json.loads(raw_text)
    except Exception as e:
        state_error = f"CompanyIntelAgent extraction failed: {e}"
        print(f"[company_intel] {state_error}")
        return {}


def _hydrate_intel(intel_dict: dict, financials: dict) -> CompanyIntel:
    """
    Maps the Claude-extracted dict onto the CompanyIntel dataclass.
    Falls back to financial data for fields Claude couldn't populate.
    """
    return CompanyIntel(
        name=intel_dict.get("name") or financials.get("company_name", ""),
        description=intel_dict.get("description") or financials.get("description", ""),
        founded_year=intel_dict.get("founded_year"),
        headquarters=intel_dict.get("headquarters") or financials.get("headquarters", ""),
        founders=intel_dict.get("founders", []),
        business_model=intel_dict.get("business_model", ""),
        funding_stage=intel_dict.get("funding_stage", ""),
        total_funding_usd=intel_dict.get("total_funding_usd"),
        key_investors=intel_dict.get("key_investors", []),
        revenue_usd=intel_dict.get("revenue_usd") or financials.get("revenue_usd"),
        employee_count=intel_dict.get("employee_count") or financials.get("employee_count"),
    )
