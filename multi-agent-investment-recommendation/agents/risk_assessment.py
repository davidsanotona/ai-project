"""
risk_assessment.py
------------------
Risk Assessment Agent — runs AFTER the parallel phase.

This agent is downstream: it consumes outputs from Company Intel, ESG, and Market agents
to produce a holistic risk picture. It also runs fresh searches for controversy and
regulatory exposure, then synthesizes everything into a risk level verdict.

Risk categories:
- Financial risk: burn rate, debt load, revenue concentration
- ESG/reputational risk: greenwashing, social controversies
- Regulatory risk: SEC actions, pending litigation, sector-specific regulation
- Market risk: competitive pressure, TAM assumptions, macro exposure

Conditional routing: if ESG score < 30, Orchestrator may skip this agent
and auto-assign HIGH risk + PASS recommendation.

Outputs: populates state.risk (RiskProfile dataclass)
"""

import json
import os
from models.state import DealState, RiskProfile
from tools.search_tools import tavily_search

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = "claude-sonnet-4-20250514"
ANTHROPIC_ENDPOINT = "https://api.anthropic.com/v1/messages"

# Threshold below which risk is automatically elevated
ESG_AUTO_HIGH_RISK_THRESHOLD = 30.0


def run(state: DealState) -> DealState:
    """
    Entry point. Reads state from all prior agents before fetching new risk data.
    """
    company = state.company_name

    # Short-circuit: if ESG score is critically low, flag immediately
    if (state.esg.overall_score is not None and
            state.esg.overall_score < ESG_AUTO_HIGH_RISK_THRESHOLD):
        state.risk = RiskProfile(
            red_flags=["ESG score below minimum threshold for this fund"],
            overall_risk_level="HIGH",
            risk_summary=f"ESG score of {state.esg.overall_score}/100 is below fund minimum. Auto-flagged HIGH risk."
        )
        return state

    # Gather fresh risk-focused search data
    search_text = _gather_risk_data(company)

    # Build a comprehensive context from all prior agent outputs
    prior_context = _build_prior_context(state)

    risk_dict = _assess_risk_with_claude(company, prior_context, search_text, state.esg.greenwashing_flags)

    state.risk = _hydrate_risk(risk_dict)
    return state


def _gather_risk_data(company: str) -> str:
    queries = [
        f"{company} SEC filing lawsuit regulatory investigation",
        f"{company} controversy scandal criticism news 2024 2025",
        f"{company} layoffs financial trouble debt",
    ]

    combined = []
    for q in queries:
        result = tavily_search(q, max_results=3)
        if result.get("answer"):
            combined.append(result["answer"])
        for r in result.get("results", []):
            combined.append(r.get("content", ""))

    return "\n\n".join(combined)


def _build_prior_context(state: DealState) -> str:
    """
    Serializes key fields from prior agents into a readable summary
    for the risk agent's prompt. Avoids passing the full state JSON
    to keep prompt size manageable.
    """
    lines = [
        f"Company: {state.intel.name}",
        f"Business model: {state.intel.business_model}",
        f"Funding stage: {state.intel.funding_stage}",
        f"Revenue: {state.intel.revenue_usd}",
        f"ESG overall score: {state.esg.overall_score}/100",
        f"ESG greenwashing flags: {', '.join(state.esg.greenwashing_flags) or 'none'}",
        f"Competitors: {', '.join(state.market.competitors[:3])}",
        f"Market growth: {state.market.growth_rate_pct}% CAGR",
    ]
    return "\n".join(lines)


def _assess_risk_with_claude(
    company: str,
    prior_context: str,
    search_text: str,
    greenwashing_flags: list[str]
) -> dict:
    import urllib.request

    flags_section = "\n".join(f"- {f}" for f in greenwashing_flags) if greenwashing_flags else "None identified"

    prompt = f"""You are a VC risk analyst conducting due diligence.

Company context from prior research:
{prior_context}

ESG greenwashing flags already identified:
{flags_section}

Fresh risk research:
{search_text}

Assess the investment risk profile. Return ONLY valid JSON:
{{
  "red_flags": ["specific red flag 1", "specific red flag 2"],
  "regulatory_risks": ["regulatory risk 1"],
  "esg_controversy": ["specific ESG controversy 1"],
  "overall_risk_level": "LOW" or "MEDIUM" or "HIGH",
  "risk_summary": "2-3 sentence risk verdict for a VC investment memo"
}}

Criteria for risk levels:
- LOW: No major red flags, clean regulatory history, ESG aligned
- MEDIUM: Minor issues or incomplete information, manageable with monitoring
- HIGH: Active litigation, greenwashing evidence, governance failure, or regulatory action

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
        print(f"[risk_assessment] failed: {e}")
        return {"overall_risk_level": "MEDIUM", "risk_summary": "Risk assessment incomplete due to error."}


def _hydrate_risk(risk_dict: dict) -> RiskProfile:
    return RiskProfile(
        red_flags=risk_dict.get("red_flags", []),
        regulatory_risks=risk_dict.get("regulatory_risks", []),
        esg_controversy=risk_dict.get("esg_controversy", []),
        overall_risk_level=risk_dict.get("overall_risk_level", "MEDIUM"),
        risk_summary=risk_dict.get("risk_summary", ""),
    )
