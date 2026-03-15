"""
tool_schemas.py
---------------
Defines all tools in MCP-compatible format (name, description, input_schema).
Each agent is also exposed as a tool so the Orchestrator can call them
using the same tool-use protocol as any external API.

Tool definition structure mirrors Anthropic's tool_use spec:
{
    "name": str,
    "description": str,
    "input_schema": { "type": "object", "properties": {...}, "required": [...] }
}
"""


# --- External data-fetching tools ---
# These are called inside individual agents to retrieve real-world data.

SEARCH_TOOL = {
    "name": "web_search",
    "description": (
        "Search the web for recent news, funding announcements, company profiles, "
        "ESG reports, and market data. Use for any information not available in "
        "structured APIs."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query string"
            }
        },
        "required": ["query"]
    }
}

FINANCE_TOOL = {
    "name": "get_financials",
    "description": (
        "Retrieve financial data for a publicly traded company using its ticker symbol. "
        "Returns revenue, market cap, P/E ratio, and recent price history."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "ticker": {
                "type": "string",
                "description": "Stock ticker symbol, e.g. TSLA, AAPL"
            }
        },
        "required": ["ticker"]
    }
}

SEC_TOOL = {
    "name": "get_sec_filings",
    "description": (
        "Fetch recent SEC filings for a US-listed company. "
        "Useful for identifying regulatory risk, revenue disclosures, and legal proceedings."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "company_name": {
                "type": "string",
                "description": "Legal company name as registered with the SEC"
            },
            "filing_type": {
                "type": "string",
                "description": "Filing type: 10-K, 10-Q, 8-K, etc.",
                "default": "10-K"
            }
        },
        "required": ["company_name"]
    }
}


# --- Sub-agent tools ---
# Each specialist agent is also declared as a tool so the Orchestrator
# can call them via the same tool-use loop, treating agents and APIs uniformly.

COMPANY_INTEL_AGENT_TOOL = {
    "name": "run_company_intel_agent",
    "description": (
        "Runs the Company Intel Agent. Researches the target company's founding team, "
        "funding history, business model, and financial overview. "
        "Returns a populated CompanyIntel object."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "company_name": {"type": "string"},
            "user_thesis": {"type": "string", "description": "VC investment thesis for context"}
        },
        "required": ["company_name"]
    }
}

ESG_AGENT_TOOL = {
    "name": "run_esg_agent",
    "description": (
        "Runs the ESG & Climate Agent. Scores the company on environmental, social, "
        "and governance dimensions. Flags greenwashing risks and maps to UN SDGs. "
        "Returns a populated ESGProfile object."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "company_name": {"type": "string"},
            "sector": {"type": "string", "description": "Company sector for ESG benchmarking"}
        },
        "required": ["company_name"]
    }
}

MARKET_AGENT_TOOL = {
    "name": "run_market_agent",
    "description": (
        "Runs the Market & Competitor Agent. Analyzes total addressable market, "
        "key competitors, and the company's competitive positioning and moat. "
        "Returns a populated MarketProfile object."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "company_name": {"type": "string"},
            "sector": {"type": "string"}
        },
        "required": ["company_name"]
    }
}

RISK_AGENT_TOOL = {
    "name": "run_risk_agent",
    "description": (
        "Runs the Risk Assessment Agent. Aggregates red flags from company intel, "
        "ESG controversies, SEC filings, and recent news. "
        "Returns a populated RiskProfile with overall risk level."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "company_name": {"type": "string"},
            "esg_flags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Greenwashing flags already identified by ESG agent"
            }
        },
        "required": ["company_name"]
    }
}

MEMO_WRITER_TOOL = {
    "name": "run_memo_writer_agent",
    "description": (
        "Runs the Memo Writer Agent. Takes the fully populated DealState and produces "
        "a professional VC investment memo in markdown format with a final "
        "INVEST / WATCH / PASS recommendation."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "deal_state_json": {
                "type": "string",
                "description": "JSON-serialized DealState containing all agent outputs"
            }
        },
        "required": ["deal_state_json"]
    }
}

# Grouped for convenient import in orchestrator
ALL_AGENT_TOOLS = [
    COMPANY_INTEL_AGENT_TOOL,
    ESG_AGENT_TOOL,
    MARKET_AGENT_TOOL,
    RISK_AGENT_TOOL,
    MEMO_WRITER_TOOL,
]
