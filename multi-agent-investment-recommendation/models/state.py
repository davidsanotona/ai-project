"""
state.py
--------
Central data model shared across all agents throughout the pipeline.
Each agent reads from and writes to this object, allowing downstream
agents to build on upstream results without tight coupling.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CompanyIntel:
    # Basic company identity resolved by the Company Intel Agent
    name: str = ""
    description: str = ""
    founded_year: Optional[int] = None
    headquarters: str = ""
    founders: list[str] = field(default_factory=list)
    business_model: str = ""
    funding_stage: str = ""        # e.g. Series A, Series B, Public
    total_funding_usd: Optional[float] = None
    key_investors: list[str] = field(default_factory=list)
    revenue_usd: Optional[float] = None
    employee_count: Optional[int] = None


@dataclass
class ESGProfile:
    # Scores produced by the ESG & Climate Agent
    overall_score: Optional[float] = None     # 0-100
    climate_score: Optional[float] = None     # 0-100, weighted toward SDG 13
    social_score: Optional[float] = None      # 0-100
    governance_score: Optional[float] = None  # 0-100
    sdg_alignment: list[str] = field(default_factory=list)   # e.g. ["SDG 7", "SDG 13"]
    greenwashing_flags: list[str] = field(default_factory=list)
    carbon_initiative: str = ""
    esg_summary: str = ""


@dataclass
class MarketProfile:
    # Produced by Market & Competitor Agent
    tam_usd: Optional[float] = None           # Total Addressable Market
    sector: str = ""
    growth_rate_pct: Optional[float] = None
    competitors: list[str] = field(default_factory=list)
    competitive_moat: str = ""
    market_summary: str = ""


@dataclass
class RiskProfile:
    # Produced by Risk Assessment Agent
    red_flags: list[str] = field(default_factory=list)
    regulatory_risks: list[str] = field(default_factory=list)
    esg_controversy: list[str] = field(default_factory=list)
    overall_risk_level: str = ""     # LOW / MEDIUM / HIGH
    risk_summary: str = ""


@dataclass
class DealState:
    """
    Top-level state object passed into every agent call.
    Orchestrator initializes this, agents populate their respective sections.
    Final state is consumed by the Memo Writer to produce the investment memo.
    """
    # User-provided inputs
    company_name: str = ""
    user_thesis: str = ""           # VC's stated investment thesis or sector interest

    # Populated progressively by each agent
    intel: CompanyIntel = field(default_factory=CompanyIntel)
    esg: ESGProfile = field(default_factory=ESGProfile)
    market: MarketProfile = field(default_factory=MarketProfile)
    risk: RiskProfile = field(default_factory=RiskProfile)

    # Final output fields
    recommendation: str = ""        # INVEST / WATCH / PASS
    memo_markdown: str = ""

    # Internal pipeline tracking
    errors: list[str] = field(default_factory=list)   # non-fatal errors from any agent
    skipped_agents: list[str] = field(default_factory=list)
