#!/usr/bin/env python3
"""Refresh dashboard cache using MCP general_search (0 API credits).

Delegates to nansen_divergence.mcp_search for comprehensive token discovery.
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from nansen_divergence.mcp_search import run_mcp_search_scan

CACHE_DIR = os.environ.get("CACHE_DIR", str(Path.home() / ".nansen-divergence"))
CACHE_PATH = os.path.join(CACHE_DIR, "cache", "latest.json")


def main():
    print("Running MCP general_search full scan (0 credits)...")
    scan_data = run_mcp_search_scan(max_tokens=150)

    results = scan_data.get("results", [])
    summary = scan_data.get("summary", {})

    print("\nResults:")
    print(f"  Tokens: {summary.get('total_tokens', 0)}")
    print(f"  Chains: {scan_data.get('chains', [])}")
    print(f"  Divergent: {summary.get('divergence_signals', 0)}")
    print(f"  HIGH confidence: {summary.get('confidence_high', 0)}")
    print(f"  MEDIUM confidence: {summary.get('confidence_medium', 0)}")
    print(f"  Radar tokens: {summary.get('sm_radar_tokens', 0)}")

    # Save to cache
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    scan_data["timestamp"] = datetime.now(timezone.utc).isoformat()
    with open(CACHE_PATH, "w") as f:
        json.dump(scan_data, f)

    print(f"\nSaved to {CACHE_PATH}")

    # Print top 10
    print("\nTop 10 by divergence strength:")
    for r in results[:10]:
        sym = r.get("token_symbol", "?")
        chain = r.get("chain", "?")
        phase = r.get("phase", "?")
        conf = r.get("confidence", "?")
        strength = r.get("divergence_strength", 0)
        narr = r.get("narrative", "")[:70]
        print(f"  {sym:10s} {chain:10s} {phase:14s} {conf:6s} {strength:.2f} | {narr}")


if __name__ == "__main__":
    main()
