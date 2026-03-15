"""
main.py
-------
CLI entry point for the VC ESG Deal Sourcing Agent.

Usage:
    python main.py --company "Tesla" --thesis "Clean energy infrastructure"
    python main.py --company "Stripe" --thesis "Fintech with ESG lens"

Outputs:
    - Prints investment memo to stdout
    - Saves memo as markdown to output/ directory
    - Saves full deal state as JSON to output/ for audit trail

Environment variables required:
    ANTHROPIC_API_KEY   — for all Claude agent calls
    TAVILY_API_KEY      — for web search (optional, uses mock data if absent)
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Ensure project root is on sys.path regardless of where script is run from
sys.path.insert(0, str(Path(__file__).parent))

from orchestrator import run_pipeline


def main():
    parser = argparse.ArgumentParser(
        description="VC ESG Deal Sourcing Agent — generates investment memos with ESG scoring"
    )
    parser.add_argument(
        "--company", "-c",
        required=True,
        help="Company name to analyze (e.g. 'Tesla', 'Northvolt', 'Form Energy')"
    )
    parser.add_argument(
        "--thesis", "-t",
        default="Climate-focused early-stage VC",
        help="Your investment thesis or focus area for context"
    )
    parser.add_argument(
        "--output-dir", "-o",
        default="output",
        help="Directory to save memo and state JSON (default: ./output)"
    )
    args = parser.parse_args()

    # Validate API key is present before starting the pipeline
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY environment variable not set.")
        print("Export it with: export ANTHROPIC_API_KEY=your_key_here")
        sys.exit(1)

    # Run the full multi-agent pipeline
    state = run_pipeline(
        company_name=args.company,
        user_thesis=args.thesis
    )

    # Handle pipeline failure (company not found or catastrophic error)
    if not state.memo_markdown and state.errors:
        print("\nPipeline encountered errors:")
        for err in state.errors:
            print(f"  - {err}")
        sys.exit(1)

    # Print memo to stdout
    print("\n" + "="*70)
    print(state.memo_markdown)
    print("="*70)

    # Save outputs
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)

    # Sanitize company name for use in filenames
    safe_name = args.company.replace(" ", "_").lower()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Save markdown memo
    memo_path = output_dir / f"memo_{safe_name}_{timestamp}.md"
    memo_path.write_text(state.memo_markdown, encoding="utf-8")
    print(f"\nMemo saved to: {memo_path}")

    # Save full state as JSON for audit trail and downstream use
    # Convert dataclass to dict manually since dataclasses don't serialize natively
    state_dict = {
        "company_name": state.company_name,
        "user_thesis": state.user_thesis,
        "recommendation": state.recommendation,
        "intel": state.intel.__dict__,
        "esg": state.esg.__dict__,
        "market": state.market.__dict__,
        "risk": state.risk.__dict__,
        "errors": state.errors,
        "skipped_agents": state.skipped_agents,
    }
    state_path = output_dir / f"state_{safe_name}_{timestamp}.json"
    state_path.write_text(json.dumps(state_dict, indent=2, default=str), encoding="utf-8")
    print(f"Full deal state saved to: {state_path}")

    # Print non-fatal errors as warnings
    if state.errors:
        print(f"\nNon-fatal warnings ({len(state.errors)}):")
        for err in state.errors:
            print(f"  - {err}")


if __name__ == "__main__":
    main()
