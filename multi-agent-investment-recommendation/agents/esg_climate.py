"""
esg_climate.py
--------------
ESG & Climate Agent — runs in parallel with Company Intel and Market agents.

Responsibilities:
- Score company on Environmental, Social, Governance dimensions (0-100 each)
- Map to relevant UN Sustainable Development Goals (SDGs)
- Flag greenwashing: detect mismatches between claims and reported actions
- Assess climate risk exposure (physical risk, transition risk)

Scoring methodology:
- Environmental (40% weight): carbon targets, renewable energy usage, CDP rating
- Social (30% weight): labor practices, supply chain, diversity disclosures
- Governance (30% weight): board independence, exec pay transparency, audit quality

Outputs: populates state.esg (ESGProfile dataclass)
"""

import json
import os
from models.state import DealState, ESGProfile
from tools.search_tools import tavily_search

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = "claude-sonnet-4-20250514"
ANTHROPIC_ENDPOINT = "https://api.anthropic.com/v1/messages"

# UN SDGs most relevant to climate/sustainability-focused VC
CLIMATE_RELEVANT_SDGS = [
    "SDG 7 (Affordable and Clean Energy)",
    "SDG 11 (Sustainable Cities)",
    "SDG 12 (Responsible Consumption)",
    "SDG 13 (Climate Action)",
    "SDG 14 (Life Below Water)",
    "SDG 15 (Life on Land)",
]


def run(state: DealState) -> DealState:
    """
    Entry point called by the Orchestrator (runs in parallel with market agent).
    """
    company = state.company_name
    sector = state.intel.business_model  # use intel from previous phase if available

    # Gather ESG-specific data points from multiple search angles
    search_text = _gather_esg_data(company)

    # Ask Claude to score and flag based on gathered data
    esg_dict = _score_esg_with_claude(company, sector, search_text)

    state.esg = _hydrate_esg(esg_dict)
    return state


def _gather_esg_data(company: str) -> str:
    """
    Runs ESG-specific searches covering sustainability reports,
    controversy news, and climate commitments.
    """
    queries = [
        f"{company} ESG sustainability report carbon emissions",
        f"{company} climate commitment net zero renewable energy",
        f"{company} ESG controversy social governance scandal",
        f"{company} greenwashing allegations environmental claims",
    ]

    combined = []
    for q in queries:
        result = tavily_search(q, max_results=3)
        if result.get("answer"):
            combined.append(result["answer"])
        for r in result.get("results", []):
            combined.append(r.get("content", ""))

    return "\n\n".join(combined)


def _score_esg_with_claude(company: str, sector: str, search_text: str) -> dict:
    """
    Asks Claude to act as an ESG analyst and return structured scores + flags.
    
    Greenwashing detection prompt engineering:
    - Instructs Claude to compare stated commitments vs verifiable actions
    - Asks for specific evidence, not just claims
    """
    import urllib.request

    # Build the SDG reference list for Claude's context
    sdg_list = "\n".join(f"- {s}" for s in CLIMATE_RELEVANT_SDGS)

    prompt = f"""You are a senior ESG analyst at a sustainability-focused VC fund.

Analyze the following data about {company} (sector: {sector or 'unknown'}).

ESG Research Data:
{search_text}

Climate-relevant UN SDGs for reference:
{sdg_list}

Instructions:
1. Score each ESG dimension from 0-100 based ONLY on evidence in the data above
2. Identify which UN SDGs this company genuinely aligns with (not just claims)
3. Flag any greenwashing: statements that appear marketing-driven without verifiable backing
4. Assign an overall ESG score as weighted average: E=40%, S=30%, G=30%

Return ONLY valid JSON with this exact structure:
{{
  "overall_score": float,
  "climate_score": float,
  "social_score": float,
  "governance_score": float,
  "sdg_alignment": ["SDG X (Name)", ...],
  "greenwashing_flags": ["specific flag 1", ...],
  "carbon_initiative": "description of their main climate initiative or empty string",
  "esg_summary": "2-3 sentence analyst summary of ESG standing"
}}

Be conservative with scores — lack of evidence should lower scores, not raise them.
Return only JSON, no explanation."""

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
            raw_text = raw_text.replace("```json", "").replace("```", "").strip()
            return json.loads(raw_text)
    except Exception as e:
        print(f"[esg_climate] scoring failed: {e}")
        return {}


def _hydrate_esg(esg_dict: dict) -> ESGProfile:
    return ESGProfile(
        overall_score=esg_dict.get("overall_score"),
        climate_score=esg_dict.get("climate_score"),
        social_score=esg_dict.get("social_score"),
        governance_score=esg_dict.get("governance_score"),
        sdg_alignment=esg_dict.get("sdg_alignment", []),
        greenwashing_flags=esg_dict.get("greenwashing_flags", []),
        carbon_initiative=esg_dict.get("carbon_initiative", ""),
        esg_summary=esg_dict.get("esg_summary", ""),
    )
