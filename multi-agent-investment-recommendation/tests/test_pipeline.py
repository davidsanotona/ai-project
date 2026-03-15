"""
tests/test_pipeline.py
----------------------
Unit tests for the VC ESG agent pipeline.

Philosophy:
- Tests use mock data only — no real API calls, no API keys needed in CI
- Each test covers a single unit of logic (one agent, one function)
- Integration tests (full pipeline) are marked separately so they can be
  skipped in CI and run manually with real keys

Run in CI:      pytest tests/ -v
Run all:        pytest tests/ -v --run-integration
"""

import sys
import os
import pytest

# Add project root to path so imports resolve without installation
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from models.state import DealState, CompanyIntel, ESGProfile, MarketProfile, RiskProfile
from tools.search_tools import _mock_search
from tools.finance_tools import _mock_financials
from tools.tool_schemas import ALL_AGENT_TOOLS


# ---------------------------------------------------------------------------
# State model tests
# ---------------------------------------------------------------------------

class TestDealState:

    def test_state_initializes_with_defaults(self):
        state = DealState(company_name="TestCorp", user_thesis="Climate VC")
        assert state.company_name == "TestCorp"
        assert state.user_thesis == "Climate VC"
        assert state.recommendation == ""
        assert state.errors == []
        assert state.skipped_agents == []

    def test_nested_dataclasses_initialize_empty(self):
        # Nested dataclasses should initialize to empty defaults, not None
        state = DealState(company_name="TestCorp")
        assert isinstance(state.intel, CompanyIntel)
        assert isinstance(state.esg, ESGProfile)
        assert isinstance(state.market, MarketProfile)
        assert isinstance(state.risk, RiskProfile)

    def test_state_fields_are_independent_across_instances(self):
        # Dataclass mutable defaults (lists) must not be shared across instances
        # This is a common Python gotcha with dataclasses and field(default_factory=list)
        state_a = DealState(company_name="CompanyA")
        state_b = DealState(company_name="CompanyB")
        state_a.errors.append("error in A")
        assert state_b.errors == [], "errors list should not be shared between instances"

    def test_intel_fields_accept_none_for_nullable(self):
        intel = CompanyIntel()
        intel.founded_year = None
        intel.total_funding_usd = None
        assert intel.founded_year is None


# ---------------------------------------------------------------------------
# Tool schema tests
# ---------------------------------------------------------------------------

class TestToolSchemas:

    def test_all_agent_tools_have_required_fields(self):
        # Every tool definition must have name, description, input_schema
        for tool in ALL_AGENT_TOOLS:
            assert "name" in tool, f"Tool missing 'name': {tool}"
            assert "description" in tool, f"Tool {tool['name']} missing 'description'"
            assert "input_schema" in tool, f"Tool {tool['name']} missing 'input_schema'"

    def test_all_tool_schemas_have_required_array(self):
        # input_schema should specify which fields are required
        for tool in ALL_AGENT_TOOLS:
            schema = tool["input_schema"]
            assert "properties" in schema, f"Tool {tool['name']} schema missing 'properties'"

    def test_five_agent_tools_defined(self):
        # Sanity check — we expect exactly 5 agent tools
        assert len(ALL_AGENT_TOOLS) == 5


# ---------------------------------------------------------------------------
# Mock data / tool tests
# ---------------------------------------------------------------------------

class TestMockTools:

    def test_mock_search_returns_answer_for_known_keys(self):
        result = _mock_search("funding rounds")
        assert "answer" in result
        assert len(result["answer"]) > 0

    def test_mock_search_returns_results_list(self):
        result = _mock_search("esg sustainability")
        assert "results" in result
        assert isinstance(result["results"], list)

    def test_mock_search_handles_unknown_query_gracefully(self):
        result = _mock_search("xyzzy unknown query 12345")
        assert "answer" in result   # should return default, not raise

    def test_mock_financials_returns_all_expected_fields(self):
        result = _mock_financials("MOCK")
        expected_fields = [
            "ticker", "company_name", "sector", "market_cap_usd",
            "revenue_usd", "gross_margin_pct", "employee_count"
        ]
        for field in expected_fields:
            assert field in result, f"Missing field: {field}"

    def test_mock_financials_uses_provided_ticker(self):
        result = _mock_financials("TSLA")
        assert result["ticker"] == "TSLA"


# ---------------------------------------------------------------------------
# Orchestrator routing logic tests
# (tests the conditional routing rules without running the full pipeline)
# ---------------------------------------------------------------------------

class TestOrchestratorRouting:

    def _make_state_with_esg(self, score: float, risk_level: str = "MEDIUM") -> DealState:
        state = DealState(company_name="TestCorp")
        state.esg.overall_score = score
        state.risk.overall_risk_level = risk_level
        return state

    def test_recommendation_is_pass_when_esg_below_40(self):
        state = self._make_state_with_esg(score=35.0, risk_level="LOW")
        recommendation = _derive_recommendation(state)
        assert recommendation == "PASS"

    def test_recommendation_is_pass_when_risk_is_high(self):
        state = self._make_state_with_esg(score=75.0, risk_level="HIGH")
        recommendation = _derive_recommendation(state)
        assert recommendation == "PASS"

    def test_recommendation_is_invest_when_strong_esg_and_low_risk(self):
        state = self._make_state_with_esg(score=75.0, risk_level="LOW")
        recommendation = _derive_recommendation(state)
        assert recommendation == "INVEST"

    def test_recommendation_is_watch_for_medium_signals(self):
        state = self._make_state_with_esg(score=55.0, risk_level="MEDIUM")
        recommendation = _derive_recommendation(state)
        assert recommendation == "WATCH"

    def test_recommendation_is_pass_when_esg_is_none(self):
        # esg score defaults to 0 when None — should be PASS
        state = DealState(company_name="TestCorp")
        state.esg.overall_score = None
        state.risk.overall_risk_level = "LOW"
        recommendation = _derive_recommendation(state)
        assert recommendation == "PASS"


# ---------------------------------------------------------------------------
# Risk agent threshold test
# ---------------------------------------------------------------------------

class TestRiskThreshold:

    def test_auto_high_risk_when_esg_critically_low(self):
        from agents.risk_assessment import ESG_AUTO_HIGH_RISK_THRESHOLD
        # Threshold should be 30 — changing it is a breaking change
        assert ESG_AUTO_HIGH_RISK_THRESHOLD == 30.0


# ---------------------------------------------------------------------------
# Helper: extracted recommendation logic for isolated unit testing
# Mirrors the logic in agents/memo_writer.py without importing Claude deps
# ---------------------------------------------------------------------------

def _derive_recommendation(state: DealState) -> str:
    esg_score = state.esg.overall_score or 0
    risk_level = state.risk.overall_risk_level or "MEDIUM"
    if esg_score < 40 or risk_level == "HIGH":
        return "PASS"
    if esg_score >= 70 and risk_level == "LOW":
        return "INVEST"
    return "WATCH"
