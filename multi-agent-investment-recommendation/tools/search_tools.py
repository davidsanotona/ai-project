"""
search_tools.py
---------------
Wraps external search APIs used by the agents.
Primary: Tavily Search API (tavily.com) — optimized for LLM-based retrieval.
Fallback: mock data for local development without API keys.

To use real data: set TAVILY_API_KEY in your environment.
"""

import os
import json
import urllib.request
import urllib.parse


TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
TAVILY_ENDPOINT = "https://api.tavily.com/search"


def tavily_search(query: str, max_results: int = 5) -> list[dict]:
    """
    Calls Tavily Search API and returns a list of result dicts.
    Each result contains: title, url, content (snippet).

    Falls back to mock results if no API key is set.
    """
    if not TAVILY_API_KEY:
        return _mock_search(query)

    payload = json.dumps({
        "api_key": TAVILY_API_KEY,
        "query": query,
        "search_depth": "advanced",
        "max_results": max_results,
        "include_answer": True        # Tavily returns a synthesized answer in addition to links
    }).encode("utf-8")

    req = urllib.request.Request(
        TAVILY_ENDPOINT,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            # Return the synthesized answer + raw results for the agent to reason over
            return {
                "answer": data.get("answer", ""),
                "results": data.get("results", [])
            }
    except Exception as e:
        # Non-fatal: return empty rather than crash the whole pipeline
        return {"answer": "", "results": [], "error": str(e)}


def _mock_search(query: str) -> dict:
    """
    Returns plausible mock search results when no API key is configured.
    Used during development and testing to avoid API costs.
    """
    mock_corpus = {
        "funding": {
            "answer": "The company raised $50M Series B in 2023 led by Andreessen Horowitz.",
            "results": [{"title": "Mock Funding News", "content": "Company raised $50M Series B in 2023."}]
        },
        "esg": {
            "answer": "The company has committed to net-zero by 2040 and publishes annual sustainability reports.",
            "results": [{"title": "Mock ESG Report", "content": "Net-zero commitment by 2040, aligned with Paris Agreement."}]
        },
        "market": {
            "answer": "The addressable market is estimated at $200B growing at 18% CAGR.",
            "results": [{"title": "Mock Market Report", "content": "TAM $200B, CAGR 18% through 2030."}]
        },
        "risk": {
            "answer": "No major regulatory actions. Minor social media controversy in Q2 2024.",
            "results": [{"title": "Mock Risk Scan", "content": "No SEC enforcement actions. Reputational risk: minor."}]
        }
    }

    # Match query keywords to mock corpus buckets
    for key in mock_corpus:
        if key in query.lower():
            return mock_corpus[key]

    # Default fallback
    return {
        "answer": f"No specific mock data found for: {query}",
        "results": [{"title": "Mock Result", "content": "Sample content for development purposes."}]
    }
