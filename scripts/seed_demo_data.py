#!/usr/bin/env python3
"""Seed realistic demo data into the cache for dashboard demonstration.

Run inside the API container or locally:
    python scripts/seed_demo_data.py

Generates multi-chain scan results with all 4 Wyckoff phases,
realistic SM flow data, and proper divergence scoring.
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from nansen_divergence.divergence import alpha_score, generate_narrative, score_divergence

# Realistic token data across 5 chains
DEMO_TOKENS = [
    # --- ETHEREUM ---
    {"chain": "ethereum", "token_address": "0x7fc66500c84a76ad7e9c93437bfc5ac33e2ddae9", "token_symbol": "AAVE", "price_usd": 267.43, "price_change": -0.082, "market_cap": 4_020_000_000, "volume_24h": 312_000_000, "market_netflow": -1_200_000, "sm_net_flow": 8_400_000, "sm_buy_volume": 12_100_000, "sm_sell_volume": 3_700_000, "sm_trader_count": 14, "sm_holdings_value": 89_000_000, "sm_holdings_change": 4_200_000},
    {"chain": "ethereum", "token_address": "0x1f9840a85d5af5bf1d1762f925bdaddc4201f984", "token_symbol": "UNI", "price_usd": 11.87, "price_change": 0.134, "market_cap": 7_120_000_000, "volume_24h": 198_000_000, "market_netflow": 3_400_000, "sm_net_flow": -5_600_000, "sm_buy_volume": 2_100_000, "sm_sell_volume": 7_700_000, "sm_trader_count": 9, "sm_holdings_value": 156_000_000, "sm_holdings_change": -8_300_000},
    {"chain": "ethereum", "token_address": "0x514910771af9ca656af840dff83e8264ecf986ca", "token_symbol": "LINK", "price_usd": 18.92, "price_change": 0.056, "market_cap": 11_800_000_000, "volume_24h": 445_000_000, "market_netflow": 2_100_000, "sm_net_flow": 3_200_000, "sm_buy_volume": 5_800_000, "sm_sell_volume": 2_600_000, "sm_trader_count": 11, "sm_holdings_value": 234_000_000, "sm_holdings_change": 5_100_000},
    {"chain": "ethereum", "token_address": "0x7d1afa7b718fb893db30a3abc0cfc608aacfebb0", "token_symbol": "MATIC", "price_usd": 0.587, "price_change": -0.041, "market_cap": 5_870_000_000, "volume_24h": 267_000_000, "market_netflow": -890_000, "sm_net_flow": 2_100_000, "sm_buy_volume": 3_400_000, "sm_sell_volume": 1_300_000, "sm_trader_count": 7, "sm_holdings_value": 67_000_000, "sm_holdings_change": 1_800_000},
    {"chain": "ethereum", "token_address": "0x6b175474e89094c44da98b954eedeac495271d0f", "token_symbol": "MKR", "price_usd": 1_845.0, "price_change": 0.023, "market_cap": 1_660_000_000, "volume_24h": 78_000_000, "market_netflow": 450_000, "sm_net_flow": 1_900_000, "sm_buy_volume": 2_800_000, "sm_sell_volume": 900_000, "sm_trader_count": 5, "sm_holdings_value": 45_000_000, "sm_holdings_change": 2_100_000},
    {"chain": "ethereum", "token_address": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2", "token_symbol": "WETH", "price_usd": 3_412.50, "price_change": 0.018, "market_cap": 410_000_000_000, "volume_24h": 12_400_000_000, "market_netflow": 45_000_000, "sm_net_flow": -12_000_000, "sm_buy_volume": 8_000_000, "sm_sell_volume": 20_000_000, "sm_trader_count": 22, "sm_holdings_value": 890_000_000, "sm_holdings_change": -15_000_000},
    {"chain": "ethereum", "token_address": "0x95ad61b0a150d79219dcf64e1e6cc01f0b64c4ce", "token_symbol": "SHIB", "price_usd": 0.0000234, "price_change": 0.187, "market_cap": 13_800_000_000, "volume_24h": 890_000_000, "market_netflow": 5_600_000, "sm_net_flow": -4_500_000, "sm_buy_volume": 1_200_000, "sm_sell_volume": 5_700_000, "sm_trader_count": 6, "sm_holdings_value": 12_000_000, "sm_holdings_change": -3_400_000},
    {"chain": "ethereum", "token_address": "0x163f8c2467924be0ae7b5347228cabf260318753", "token_symbol": "WLD", "price_usd": 2.34, "price_change": -0.156, "market_cap": 1_870_000_000, "volume_24h": 234_000_000, "market_netflow": -3_200_000, "sm_net_flow": 6_700_000, "sm_buy_volume": 8_900_000, "sm_sell_volume": 2_200_000, "sm_trader_count": 8, "sm_holdings_value": 34_000_000, "sm_holdings_change": 5_600_000},
    # --- BNB ---
    {"chain": "bnb", "token_address": "0xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c", "token_symbol": "WBNB", "price_usd": 612.30, "price_change": 0.032, "market_cap": 94_000_000_000, "volume_24h": 1_200_000_000, "market_netflow": 8_900_000, "sm_net_flow": 4_500_000, "sm_buy_volume": 6_700_000, "sm_sell_volume": 2_200_000, "sm_trader_count": 15, "sm_holdings_value": 345_000_000, "sm_holdings_change": 6_700_000},
    {"chain": "bnb", "token_address": "0x0e09fabb73bd3ade0a17ecc321fd13a19e81ce82", "token_symbol": "CAKE", "price_usd": 2.87, "price_change": -0.094, "market_cap": 876_000_000, "volume_24h": 67_000_000, "market_netflow": -1_100_000, "sm_net_flow": 3_200_000, "sm_buy_volume": 4_500_000, "sm_sell_volume": 1_300_000, "sm_trader_count": 8, "sm_holdings_value": 23_000_000, "sm_holdings_change": 2_800_000},
    {"chain": "bnb", "token_address": "0x2170ed0880ac9a755fd29b2688956bd959f933f8", "token_symbol": "ETH", "price_usd": 3_410.00, "price_change": 0.019, "market_cap": 410_000_000_000, "volume_24h": 890_000_000, "market_netflow": 12_000_000, "sm_net_flow": -3_400_000, "sm_buy_volume": 1_200_000, "sm_sell_volume": 4_600_000, "sm_trader_count": 6, "sm_holdings_value": 78_000_000, "sm_holdings_change": -2_100_000},
    {"chain": "bnb", "token_address": "0x1d2f0da169ceb9fc7b3144628db156f3f6c60dbe", "token_symbol": "XRP", "price_usd": 2.14, "price_change": -0.067, "market_cap": 123_000_000_000, "volume_24h": 4_500_000_000, "market_netflow": -5_600_000, "sm_net_flow": 1_800_000, "sm_buy_volume": 2_900_000, "sm_sell_volume": 1_100_000, "sm_trader_count": 5, "sm_holdings_value": 18_000_000, "sm_holdings_change": 900_000},
    {"chain": "bnb", "token_address": "0x7130d2a12b9bcbfae4f2634d864a1ee1ce3ead9c", "token_symbol": "BTCB", "price_usd": 87_234.00, "price_change": 0.045, "market_cap": 1_700_000_000_000, "volume_24h": 34_000_000_000, "market_netflow": 67_000_000, "sm_net_flow": -8_900_000, "sm_buy_volume": 3_400_000, "sm_sell_volume": 12_300_000, "sm_trader_count": 12, "sm_holdings_value": 456_000_000, "sm_holdings_change": -7_800_000},
    # --- SOLANA ---
    {"chain": "solana", "token_address": "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN", "token_symbol": "JUP", "price_usd": 1.23, "price_change": -0.112, "market_cap": 1_660_000_000, "volume_24h": 234_000_000, "market_netflow": -4_500_000, "sm_net_flow": 7_800_000, "sm_buy_volume": 10_200_000, "sm_sell_volume": 2_400_000, "sm_trader_count": 16, "sm_holdings_value": 56_000_000, "sm_holdings_change": 6_700_000},
    {"chain": "solana", "token_address": "orcaEKTdK7LKz57vaAYr9QeNsVEPfiu6QeMU1kektZE", "token_symbol": "ORCA", "price_usd": 4.56, "price_change": 0.078, "market_cap": 234_000_000, "volume_24h": 45_000_000, "market_netflow": 890_000, "sm_net_flow": 1_200_000, "sm_buy_volume": 1_800_000, "sm_sell_volume": 600_000, "sm_trader_count": 4, "sm_holdings_value": 8_900_000, "sm_holdings_change": 1_100_000},
    {"chain": "solana", "token_address": "rndrizKT3MK1iimdxRdWabcF7Zg7AR5T4nud4EkHBof", "token_symbol": "RNDR", "price_usd": 8.92, "price_change": 0.145, "market_cap": 4_670_000_000, "volume_24h": 345_000_000, "market_netflow": 6_700_000, "sm_net_flow": -5_600_000, "sm_buy_volume": 2_300_000, "sm_sell_volume": 7_900_000, "sm_trader_count": 9, "sm_holdings_value": 67_000_000, "sm_holdings_change": -4_500_000},
    {"chain": "solana", "token_address": "WENWENvqqNya429ubCdR81ZmD69brwQaaBYY6p3LCpk", "token_symbol": "WEN", "price_usd": 0.000089, "price_change": -0.234, "market_cap": 67_000_000, "volume_24h": 12_000_000, "market_netflow": -890_000, "sm_net_flow": 2_300_000, "sm_buy_volume": 3_100_000, "sm_sell_volume": 800_000, "sm_trader_count": 7, "sm_holdings_value": 4_500_000, "sm_holdings_change": 1_900_000},
    {"chain": "solana", "token_address": "HZ1JovNiVvGrGNiiYvEozEVgZ58xaU3RKwRMDBVT2bes", "token_symbol": "PYTH", "price_usd": 0.467, "price_change": -0.045, "market_cap": 2_100_000_000, "volume_24h": 123_000_000, "market_netflow": -1_200_000, "sm_net_flow": 890_000, "sm_buy_volume": 1_400_000, "sm_sell_volume": 510_000, "sm_trader_count": 3, "sm_holdings_value": 23_000_000, "sm_holdings_change": 450_000},
    # --- BASE ---
    {"chain": "base", "token_address": "0x940181a94a35a4569e4529a3cdfb74e38fd98631", "token_symbol": "AERO", "price_usd": 1.87, "price_change": 0.167, "market_cap": 1_120_000_000, "volume_24h": 156_000_000, "market_netflow": 4_500_000, "sm_net_flow": -6_700_000, "sm_buy_volume": 1_800_000, "sm_sell_volume": 8_500_000, "sm_trader_count": 11, "sm_holdings_value": 34_000_000, "sm_holdings_change": -5_600_000},
    {"chain": "base", "token_address": "0x4ed4e862860bed51a9570b96d89af5e1b0efefed", "token_symbol": "DEGEN", "price_usd": 0.0123, "price_change": -0.189, "market_cap": 145_000_000, "volume_24h": 34_000_000, "market_netflow": -2_300_000, "sm_net_flow": 4_500_000, "sm_buy_volume": 5_600_000, "sm_sell_volume": 1_100_000, "sm_trader_count": 13, "sm_holdings_value": 7_800_000, "sm_holdings_change": 3_400_000},
    {"chain": "base", "token_address": "0x532f27101965dd16442e59d40670faf5ebb142e4", "token_symbol": "BRETT", "price_usd": 0.156, "price_change": 0.089, "market_cap": 1_560_000_000, "volume_24h": 89_000_000, "market_netflow": 1_200_000, "sm_net_flow": 2_300_000, "sm_buy_volume": 3_400_000, "sm_sell_volume": 1_100_000, "sm_trader_count": 6, "sm_holdings_value": 12_000_000, "sm_holdings_change": 1_800_000},
    {"chain": "base", "token_address": "0xd5046b976188eb40f6de40fb527f89c05b086dfd", "token_symbol": "BSX", "price_usd": 0.234, "price_change": -0.078, "market_cap": 89_000_000, "volume_24h": 12_000_000, "market_netflow": -450_000, "sm_net_flow": 1_200_000, "sm_buy_volume": 1_800_000, "sm_sell_volume": 600_000, "sm_trader_count": 4, "sm_holdings_value": 3_400_000, "sm_holdings_change": 890_000},
    # --- ARBITRUM ---
    {"chain": "arbitrum", "token_address": "0x912ce59144191c1204e64559fe8253a0e49e6548", "token_symbol": "ARB", "price_usd": 1.34, "price_change": 0.056, "market_cap": 5_360_000_000, "volume_24h": 456_000_000, "market_netflow": 3_400_000, "sm_net_flow": -4_500_000, "sm_buy_volume": 2_100_000, "sm_sell_volume": 6_600_000, "sm_trader_count": 8, "sm_holdings_value": 89_000_000, "sm_holdings_change": -3_200_000},
    {"chain": "arbitrum", "token_address": "0xfc5a1a6eb076a2c7ad06ed22c90d7e710e35ad0a", "token_symbol": "GMX", "price_usd": 34.56, "price_change": -0.034, "market_cap": 345_000_000, "volume_24h": 23_000_000, "market_netflow": -890_000, "sm_net_flow": 2_100_000, "sm_buy_volume": 3_200_000, "sm_sell_volume": 1_100_000, "sm_trader_count": 5, "sm_holdings_value": 18_000_000, "sm_holdings_change": 1_500_000},
    {"chain": "arbitrum", "token_address": "0x539bde0d7dbd336b79148aa742883198bbf60342", "token_symbol": "MAGIC", "price_usd": 0.89, "price_change": 0.234, "market_cap": 267_000_000, "volume_24h": 34_000_000, "market_netflow": 2_300_000, "sm_net_flow": -3_400_000, "sm_buy_volume": 800_000, "sm_sell_volume": 4_200_000, "sm_trader_count": 6, "sm_holdings_value": 5_600_000, "sm_holdings_change": -2_800_000},
    {"chain": "arbitrum", "token_address": "0x3d9907f9a368ad0a51be60f7da3b97cf940982d8", "token_symbol": "GRAIL", "price_usd": 2_345.00, "price_change": -0.067, "market_cap": 78_000_000, "volume_24h": 8_900_000, "market_netflow": -340_000, "sm_net_flow": 890_000, "sm_buy_volume": 1_200_000, "sm_sell_volume": 310_000, "sm_trader_count": 3, "sm_holdings_value": 4_500_000, "sm_holdings_change": 670_000},
]

# SM Radar tokens (extra tokens with SM activity not in main results)
DEMO_RADAR = [
    {"chain": "ethereum", "token_address": "0xae78736cd615f374d3085123a210448e74fc6393", "token_symbol": "rETH", "sm_net_flow_24h": 12_300_000, "sm_net_flow_7d": 45_000_000, "sm_trader_count": 18, "sm_sectors": ["DeFi", "LST"], "market_cap": 6_700_000_000},
    {"chain": "ethereum", "token_address": "0xbe9895146f7af43049ca1c1ae358b0541ea49704", "token_symbol": "cbETH", "sm_net_flow_24h": -8_900_000, "sm_net_flow_7d": -23_000_000, "sm_trader_count": 12, "sm_sectors": ["DeFi", "LST"], "market_cap": 3_400_000_000},
    {"chain": "solana", "token_address": "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm", "token_symbol": "WIF", "sm_net_flow_24h": 5_600_000, "sm_net_flow_7d": 18_000_000, "sm_trader_count": 14, "sm_sectors": ["Meme"], "market_cap": 2_300_000_000},
    {"chain": "base", "token_address": "0x0578d8a44db98b23bf096a382e016e29a5ce0ffe", "token_symbol": "HIGHER", "sm_net_flow_24h": 3_400_000, "sm_net_flow_7d": 8_900_000, "sm_trader_count": 9, "sm_sectors": ["Meme", "Social"], "market_cap": 89_000_000},
    {"chain": "bnb", "token_address": "0xce7de646e7208a4ef112cb6ed5038fa6cc6b12e3", "token_symbol": "TRX", "sm_net_flow_24h": -4_500_000, "sm_net_flow_7d": -12_000_000, "sm_trader_count": 7, "sm_sectors": ["L1"], "market_cap": 12_000_000_000},
    {"chain": "arbitrum", "token_address": "0x5979d7b546e38e9ab8f7696ef2c2c9e3be8e0c89", "token_symbol": "wstETH", "sm_net_flow_24h": 7_800_000, "sm_net_flow_7d": 34_000_000, "sm_trader_count": 15, "sm_sectors": ["DeFi", "LST"], "market_cap": 8_900_000_000},
    {"chain": "solana", "token_address": "bonk1ARF9KY7DP2hpYgzkWBGLSNh9sYHC2fNT2Qqaei", "token_symbol": "BONK", "sm_net_flow_24h": -2_300_000, "sm_net_flow_7d": -5_600_000, "sm_trader_count": 8, "sm_sectors": ["Meme"], "market_cap": 1_200_000_000},
    {"chain": "ethereum", "token_address": "0x6982508145454ce325ddbe47a25d4ec3d2311933", "token_symbol": "PEPE", "sm_net_flow_24h": 9_100_000, "sm_net_flow_7d": 28_000_000, "sm_trader_count": 21, "sm_sectors": ["Meme"], "market_cap": 5_600_000_000},
]


def build_results() -> list[dict]:
    """Score and enrich demo tokens using the real divergence engine."""
    results = []
    for token in DEMO_TOKENS:
        scoring_flow = token["sm_net_flow"] if token["sm_net_flow"] != 0 else token["market_netflow"]
        strength, phase, confidence = score_divergence(
            sm_net_flow=scoring_flow,
            price_change_pct=token["price_change"],
            market_cap=token["market_cap"],
            trader_count=token["sm_trader_count"],
            holdings_change=token["sm_holdings_change"],
        )

        token_data = {
            **token,
            "sm_wallet_labels": [],
            "divergence_strength": strength,
            "phase": phase,
            "confidence": confidence,
            "has_sm_data": True,
            "alpha_score": alpha_score(strength),
            "narrative": "",
        }
        token_data["narrative"] = generate_narrative(token_data)
        results.append(token_data)

    results.sort(key=lambda x: x["divergence_strength"], reverse=True)
    return results


def build_summary(results: list[dict], radar: list[dict]) -> dict:
    """Build summary stats from results."""
    from nansen_divergence.divergence import is_divergent

    divergent = [r for r in results if is_divergent(r["phase"])]
    with_sm = [r for r in results if r.get("has_sm_data")]
    return {
        "total_tokens": len(results),
        "with_sm_data": len(with_sm),
        "sm_data_pct": round(len(with_sm) / len(results) * 100, 1) if results else 0,
        "sm_radar_tokens": len(radar),
        "divergence_signals": len(divergent),
        "accumulation": len([r for r in results if r["phase"] == "ACCUMULATION"]),
        "distribution": len([r for r in results if r["phase"] == "DISTRIBUTION"]),
        "confidence_high": len([r for r in results if r["confidence"] == "HIGH"]),
        "confidence_medium": len([r for r in results if r["confidence"] == "MEDIUM"]),
        "confidence_low": len([r for r in results if r["confidence"] == "LOW"]),
    }


def main():
    results = build_results()
    radar = DEMO_RADAR
    summary = build_summary(results, radar)

    # Backtest stats (realistic demo values)
    backtest = {
        "total_signals": 47,
        "wins": 31,
        "losses": 16,
        "win_rate": 65.96,
        "avg_return": 8.4,
        "best_return": 34.2,
        "worst_return": -12.8,
    }

    scan_data = {
        "results": results,
        "radar": radar,
        "summary": summary,
        "chains": ["ethereum", "bnb", "solana", "base", "arbitrum"],
        "validations": [],
        "backtest": backtest,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "demo_mode": True,
    }

    # Save to cache location
    cache_dir = os.path.join(os.path.expanduser("~"), ".nansen-divergence", "cache")
    os.makedirs(cache_dir, exist_ok=True)
    path = os.path.join(cache_dir, "latest.json")

    with open(path, "w") as f:
        json.dump(scan_data, f, indent=2)

    print(f"Seeded demo data to {path}")
    print(f"  Tokens: {len(results)} across {len(set(r['chain'] for r in results))} chains")
    print(f"  Phases: {dict((p, len([r for r in results if r['phase'] == p])) for p in ['ACCUMULATION', 'DISTRIBUTION', 'MARKUP', 'MARKDOWN'])}")
    print(f"  HIGH confidence: {summary['confidence_high']}")
    print(f"  MEDIUM confidence: {summary['confidence_medium']}")
    print(f"  Radar tokens: {len(radar)}")
    print(f"  SM data coverage: {summary['sm_data_pct']}%")


if __name__ == "__main__":
    main()
