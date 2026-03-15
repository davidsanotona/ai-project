"""
orchestrator.py
---------------
Orchestrator Agent — the central coordinator of the multi-agent pipeline.

This is the "brain" of the system. It does not do research itself;
it manages execution order, shared state, conditional routing, and error recovery.

Execution flow:
  Phase 1 (Sequential):  Company Intel Agent
                          └── needed by all downstream agents for sector/context
  Phase 2 (Parallel):    ESG Agent + Market Agent run concurrently via threads
                          └── both independent of each other, both depend on Phase 1
  Phase 3 (Sequential):  Risk Assessment Agent
                          └── consumes ESG + Market outputs
  Phase 4 (Conditional): Memo Writer Agent
                          └── skipped only if a catastrophic error empties all state

Conditional routing rules:
  - If ESG score < 30: Risk agent is skipped, auto-assign HIGH/PASS
  - If any agent fails: error is logged in state.errors, pipeline continues
  - If company not found at all: abort early with meaningful error

MCP Protocol note:
  In a production MCP setup, each agent would be a separate MCP server
  and the orchestrator would call them via tool_use messages. Here,
  we simulate that by calling agent run() functions directly but structuring
  the call pattern identically to how tool_use would work.
"""

import concurrent.futures
import json
import os
from models.state import DealState
from agents import company_intel, esg_climate, market_analysis, risk_assessment, memo_writer


def run_pipeline(company_name: str, user_thesis: str = "") -> DealState:
    """
    Main entry point. Accepts user inputs, runs full agent pipeline,
    returns the final populated DealState including the investment memo.
    """
    # Initialize shared state object — all agents read/write this
    state = DealState(
        company_name=company_name,
        user_thesis=user_thesis
    )

    print(f"\n[orchestrator] Starting pipeline for: {company_name}")

    # -------------------------------------------------------------------------
    # Phase 1: Company Intel (Sequential)
    # Must run first — provides sector context that ESG and Market agents use
    # -------------------------------------------------------------------------
    print("[orchestrator] Phase 1: Company Intel Agent")
    state = _run_agent_safe(state, company_intel.run, "CompanyIntelAgent")

    # Early abort: if we got no company data at all, there's nothing to analyze
    if not state.intel.name and not state.intel.description:
        state.errors.append("CompanyIntelAgent returned no data. Cannot proceed.")
        print(f"[orchestrator] Aborting pipeline — company not found: {company_name}")
        return state

    # -------------------------------------------------------------------------
    # Phase 2: ESG + Market (Parallel using ThreadPoolExecutor)
    # These two agents are independent — running them concurrently halves wait time
    # ThreadPoolExecutor is appropriate here since both agents are I/O bound (API calls)
    # -------------------------------------------------------------------------
    print("[orchestrator] Phase 2: ESG + Market Agents (parallel)")
    state = _run_parallel_agents(state, [
        (esg_climate.run, "ESGClimateAgent"),
        (market_analysis.run, "MarketAnalysisAgent"),
    ])

    # -------------------------------------------------------------------------
    # Conditional routing: skip risk agent if ESG is critically low
    # Orchestrator makes this decision — not the risk agent itself
    # -------------------------------------------------------------------------
    esg_score = state.esg.overall_score
    if esg_score is not None and esg_score < 30:
        print(f"[orchestrator] ESG score {esg_score} below threshold — auto-routing to PASS, skipping Risk Agent")
        state.risk.overall_risk_level = "HIGH"
        state.risk.risk_summary = f"ESG score {esg_score}/100 is below fund minimum threshold of 30. Auto-PASS."
        state.skipped_agents.append("RiskAssessmentAgent")
    else:
        # -------------------------------------------------------------------------
        # Phase 3: Risk Assessment (Sequential — depends on Phase 2 outputs)
        # -------------------------------------------------------------------------
        print("[orchestrator] Phase 3: Risk Assessment Agent")
        state = _run_agent_safe(state, risk_assessment.run, "RiskAssessmentAgent")

    # -------------------------------------------------------------------------
    # Phase 4: Memo Writer (Sequential — depends on all prior agents)
    # -------------------------------------------------------------------------
    print("[orchestrator] Phase 4: Memo Writer Agent")
    state = _run_agent_safe(state, memo_writer.run, "MemoWriterAgent")

    print(f"[orchestrator] Pipeline complete. Recommendation: {state.recommendation}")
    return state


def _run_agent_safe(state: DealState, agent_fn, agent_name: str) -> DealState:
    """
    Wraps an agent call in try/except so one agent failure does not crash
    the entire pipeline. Errors are logged in state.errors for transparency.
    """
    try:
        return agent_fn(state)
    except Exception as e:
        error_msg = f"{agent_name} failed: {str(e)}"
        print(f"[orchestrator] ERROR — {error_msg}")
        state.errors.append(error_msg)
        return state  # return unchanged state, downstream agents handle missing data


def _run_parallel_agents(state: DealState, agents: list[tuple]) -> DealState:
    """
    Runs multiple agents concurrently using threads.

    Problem with shared state in parallel:
    Since both agents write to different fields of the same DealState object
    (esg_climate writes to state.esg, market writes to state.market),
    we pass a copy-like approach: each agent runs on the same state instance
    but writes to non-overlapping fields. This avoids race conditions without
    needing locks, because Python's GIL and field-level isolation keep writes safe
    when agents touch disjoint attributes.

    In a true MCP deployment, each agent would run in its own process/container
    and return a partial result, which the orchestrator merges — same pattern.
    """
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(agents)) as executor:
        futures = {
            executor.submit(_run_agent_safe, state, fn, name): name
            for fn, name in agents
        }
        # Collect results — we don't need return values since agents mutate state in-place
        for future in concurrent.futures.as_completed(futures):
            agent_name = futures[future]
            try:
                future.result()   # raises if the agent threw an uncaught exception
            except Exception as e:
                print(f"[orchestrator] Parallel agent {agent_name} raised: {e}")

    return state
