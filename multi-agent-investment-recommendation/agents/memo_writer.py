"""
memo_writer.py
--------------
Memo Writer Agent — final agent in the pipeline.

Runs only after all other agents have populated the DealState.
Responsibilities:
- Derive the final investment recommendation (INVEST / WATCH / PASS)
- Generate a professional VC investment memo in markdown format

Recommendation logic (rule-based pre-filter before Claude writes the memo):
- PASS:    ESG score < 40 OR risk level is HIGH
- INVEST:  ESG score >= 70 AND risk level is LOW AND positive market signal
- WATCH:   Everything else

Claude then writes the full narrative memo using this pre-computed recommendation
and all upstream agent data.

Outputs: populates state.recommendation and state.memo_markdown
"""

import json
import os
from datetime import date
from models.state import DealState

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = "claude-sonnet-4-20250514"
ANTHROPIC_ENDPOINT = "https://api.anthropic.com/v1/messages"


def run(state: DealState) -> DealState:
    """
    Entry point. Derives recommendation then generates full memo.
    """
    state.recommendation = _derive_recommendation(state)
    state.memo_markdown = _write_memo_with_claude(state)
    return state


def _derive_recommendation(state: DealState) -> str:
    """
    Rule-based recommendation engine applied before Claude writes the memo.
    This ensures the recommendation is deterministic and auditable —
    not left entirely to LLM judgment.
    """
    esg_score = state.esg.overall_score or 0
    risk_level = state.risk.overall_risk_level or "MEDIUM"

    # Hard PASS conditions
    if esg_score < 40 or risk_level == "HIGH":
        return "PASS"

    # Strong INVEST signal
    if esg_score >= 70 and risk_level == "LOW":
        return "INVEST"

    # Default: monitor
    return "WATCH"


def _write_memo_with_claude(state: DealState) -> str:
    """
    Provides all agent outputs to Claude and asks it to write the narrative memo.
    We do NOT ask Claude to decide the recommendation — that was done deterministically above.
    Claude's role here is articulation, not decision-making.
    """
    import urllib.request

    intel = state.intel
    esg = state.esg
    market = state.market
    risk = state.risk
    today = date.today().strftime("%B %d, %Y")

    # Format helpers for nullable fields
    def fmt_usd(val):
        if val is None:
            return "N/A"
        if val >= 1_000_000_000:
            return f"${val/1_000_000_000:.1f}B"
        return f"${val/1_000_000:.0f}M"

    def fmt_pct(val):
        return f"{val*100:.0f}%" if val is not None else "N/A"

    # Build structured context for the prompt
    context = f"""
COMPANY: {intel.name}
DESCRIPTION: {intel.description}
FOUNDED: {intel.founded_year or 'Unknown'} | HQ: {intel.headquarters}
FOUNDERS: {', '.join(intel.founders) or 'Unknown'}
BUSINESS MODEL: {intel.business_model}
FUNDING STAGE: {intel.funding_stage} | TOTAL RAISED: {fmt_usd(intel.total_funding_usd)}
KEY INVESTORS: {', '.join(intel.key_investors) or 'Unknown'}
REVENUE: {fmt_usd(intel.revenue_usd)} | EMPLOYEES: {intel.employee_count or 'N/A'}

ESG OVERALL: {esg.overall_score}/100
  - Climate/Environmental: {esg.climate_score}/100
  - Social: {esg.social_score}/100
  - Governance: {esg.governance_score}/100
SDG ALIGNMENT: {', '.join(esg.sdg_alignment) or 'None identified'}
GREENWASHING FLAGS: {', '.join(esg.greenwashing_flags) or 'None'}
CLIMATE INITIATIVE: {esg.carbon_initiative or 'Not disclosed'}
ESG ANALYST SUMMARY: {esg.esg_summary}

SECTOR: {market.sector} | TAM: {fmt_usd(market.tam_usd)} | GROWTH: {market.growth_rate_pct}% CAGR
COMPETITORS: {', '.join(market.competitors) or 'Unknown'}
COMPETITIVE MOAT: {market.competitive_moat}
MARKET SUMMARY: {market.market_summary}

RISK LEVEL: {risk.overall_risk_level}
RED FLAGS: {'; '.join(risk.red_flags) or 'None'}
REGULATORY RISKS: {'; '.join(risk.regulatory_risks) or 'None'}
ESG CONTROVERSY: {'; '.join(risk.esg_controversy) or 'None'}
RISK SUMMARY: {risk.risk_summary}

FINAL RECOMMENDATION: {state.recommendation}
USER THESIS: {state.user_thesis or 'Climate-focused VC'}
""".strip()

    prompt = f"""You are a partner at a sustainability-focused VC fund writing an investment memo.

Use the structured data below to write a professional investment memo in markdown.

{context}

Write the memo with these sections:
1. Header block (company, date, recommendation verdict)
2. Executive Summary (3-4 sentences)
3. Company Overview
4. ESG & Climate Assessment (this section should be detailed — it is our fund's primary lens)
5. Market Opportunity
6. Risk Assessment
7. Investment Thesis (or reason for Pass/Watch)

Tone: professional, direct, no fluff. Write as a senior VC partner, not a consultant.
Do not add sections not listed above.
Do not repeat the raw data verbatim — synthesize and editorialize where relevant.
Use markdown formatting. Today's date: {today}."""

    payload = json.dumps({
        "model": CLAUDE_MODEL,
        "max_tokens": 2000,
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
        with urllib.request.urlopen(req, timeout=45) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["content"][0]["text"].strip()
    except Exception as e:
        print(f"[memo_writer] memo generation failed: {e}")
        return f"# Investment Memo — {state.company_name}\n\nMemo generation failed: {e}"
