"""Demo data generator — produces realistic scan data when API credits are exhausted."""

import hashlib
import math
import random
import time
from datetime import datetime, timezone

# Real tokens across chains for convincing demo data
_TOKENS = [
    # Ethereum
    {"chain": "ethereum", "symbol": "PEPE", "address": "0x6982508145454ce325ddbe47a25d4ec3d2311933", "mcap": 3_400_000_000, "price": 0.0000082},
    {"chain": "ethereum", "symbol": "UNI", "address": "0x1f9840a85d5af5bf1d1762f925bdaddc4201f984", "mcap": 5_800_000_000, "price": 7.42},
    {"chain": "ethereum", "symbol": "AAVE", "address": "0x7fc66500c84a76ad7e9c93437bfc5ac33e2ddae9", "mcap": 3_200_000_000, "price": 213.5},
    {"chain": "ethereum", "symbol": "LDO", "address": "0x5a98fcbea516cf06857215779fd812ca3bef1b32", "mcap": 1_700_000_000, "price": 1.92},
    {"chain": "ethereum", "symbol": "ENS", "address": "0xc18360217d8f7ab5e7c516566761ea12ce7f9d72", "mcap": 780_000_000, "price": 25.3},
    {"chain": "ethereum", "symbol": "PENDLE", "address": "0x808507121b80c02388fad14726482e061b8da827", "mcap": 620_000_000, "price": 3.87},
    {"chain": "ethereum", "symbol": "rETH", "address": "0xae78736cd615f374d3085123a210448e74fc6393", "mcap": 6_700_000_000, "price": 3890.0},
    {"chain": "ethereum", "symbol": "EIGEN", "address": "0xec53bf9167f50cdeb3ae105f56099aaab9061f83", "mcap": 1_100_000_000, "price": 1.65},
    # BNB
    {"chain": "bnb", "symbol": "CAKE", "address": "0x0e09fabb73bd3ade0a17ecc321fd13a19e81ce82", "mcap": 640_000_000, "price": 2.58},
    {"chain": "bnb", "symbol": "XVS", "address": "0xcf6bb5389c92bdda8a3747ddb454cb7a64626c63", "mcap": 120_000_000, "price": 8.12},
    {"chain": "bnb", "symbol": "BAKE", "address": "0xe02df9e3e622debdd69fb838bb799e3f168902c5", "mcap": 85_000_000, "price": 0.34},
    {"chain": "bnb", "symbol": "FLOKI", "address": "0xfb5b838b6cfeedc2873ab27866079ac55363d37e", "mcap": 1_200_000_000, "price": 0.000128},
    {"chain": "bnb", "symbol": "ID", "address": "0x2dff88a56767223a5529ea5960da7a3f5f766406", "mcap": 310_000_000, "price": 0.42},
    # Solana
    {"chain": "solana", "symbol": "JUP", "address": "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN", "mcap": 1_500_000_000, "price": 1.12},
    {"chain": "solana", "symbol": "WIF", "address": "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm", "mcap": 780_000_000, "price": 0.78},
    {"chain": "solana", "symbol": "BONK", "address": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263", "mcap": 1_100_000_000, "price": 0.0000165},
    {"chain": "solana", "symbol": "RAY", "address": "4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R", "mcap": 540_000_000, "price": 2.06},
    {"chain": "solana", "symbol": "RENDER", "address": "rndrizKT3MK1iimdxRdWabcF7Zg7AR5T4nud4EkHBof", "mcap": 2_800_000_000, "price": 5.34},
    # Base
    {"chain": "base", "symbol": "DEGEN", "address": "0x4ed4e862860bed51a9570b96d89af5e1b0efefed", "mcap": 145_000_000, "price": 0.0123},
    {"chain": "base", "symbol": "AERO", "address": "0x940181a94a35a4569e4529a3cdfb74e38fd98631", "mcap": 1_120_000_000, "price": 1.87},
    {"chain": "base", "symbol": "BRETT", "address": "0x532f27101965dd16442e59d40670faf5ebb142e4", "mcap": 480_000_000, "price": 0.048},
    {"chain": "base", "symbol": "VIRTUAL", "address": "0x0b3e328455c4059eeb9e3f84b5543f74e24e7e1b", "mcap": 620_000_000, "price": 1.23},
    # Arbitrum
    {"chain": "arbitrum", "symbol": "ARB", "address": "0x912ce59144191c1204e64559fe8253a0e49e6548", "mcap": 3_100_000_000, "price": 0.78},
    {"chain": "arbitrum", "symbol": "GMX", "address": "0xfc5a1a6eb076a2c7ad06ed22c90d7e710e35ad0a", "mcap": 340_000_000, "price": 35.6},
    {"chain": "arbitrum", "symbol": "MAGIC", "address": "0x539bde0d7dbd336b79148aa742883198bbf60342", "mcap": 180_000_000, "price": 0.45},
    {"chain": "arbitrum", "symbol": "GNS", "address": "0x18c11fd286c5ec11c3b683caa813b77f5163a122", "mcap": 95_000_000, "price": 2.78},
]

_SECTORS = ["DeFi", "LST", "Meme", "L2", "Gaming", "AI", "RWA", "DEX", "Lending", "NFT"]
_SECTOR_MAP = {
    "PEPE": ["Meme"], "UNI": ["DEX", "DeFi"], "AAVE": ["Lending", "DeFi"],
    "LDO": ["LST", "DeFi"], "ENS": ["DeFi"], "PENDLE": ["DeFi", "LST"],
    "rETH": ["LST", "DeFi"], "EIGEN": ["LST", "DeFi"],
    "CAKE": ["DEX", "DeFi"], "XVS": ["Lending", "DeFi"], "BAKE": ["DeFi"],
    "FLOKI": ["Meme"], "ID": ["DeFi"],
    "JUP": ["DEX", "DeFi"], "WIF": ["Meme"], "BONK": ["Meme"],
    "RAY": ["DEX", "DeFi"], "RENDER": ["AI"],
    "DEGEN": ["Meme"], "AERO": ["DEX", "DeFi"], "BRETT": ["Meme"],
    "VIRTUAL": ["AI"],
    "ARB": ["L2"], "GMX": ["DEX", "DeFi"], "MAGIC": ["Gaming"], "GNS": ["DeFi"],
}


def _seeded_random(seed_str: str) -> random.Random:
    """Create a deterministic Random instance seeded by string + hour.

    Changes every hour so the dashboard shows evolving data.
    """
    hour_key = int(time.time()) // 3600
    seed = int(hashlib.md5(f"{seed_str}:{hour_key}".encode()).hexdigest()[:8], 16)
    return random.Random(seed)


def generate_demo_scan(chains: list[str] | None = None) -> dict:
    """Generate realistic demo scan data.

    Data is deterministic per hour so repeated calls return consistent results,
    but shifts each hour to simulate a live scanner.
    """
    rng = _seeded_random("demo_scan")
    if chains is None:
        chains = ["ethereum", "bnb", "solana", "base", "arbitrum"]

    tokens = [t for t in _TOKENS if t["chain"] in chains]
    rng.shuffle(tokens)

    results = []
    radar = []

    for t in tokens:
        # Vary price/mcap slightly per hour
        price_jitter = rng.uniform(0.85, 1.15)
        mcap = t["mcap"] * price_jitter
        price = t["price"] * price_jitter

        # Random phase assignment with realistic distribution
        phase_roll = rng.random()
        if phase_roll < 0.40:
            phase = "ACCUMULATION"
            price_change = -rng.uniform(0.03, 0.35)
            sm_flow = rng.uniform(100_000, 8_000_000)
        elif phase_roll < 0.70:
            phase = "DISTRIBUTION"
            price_change = rng.uniform(0.03, 0.30)
            sm_flow = -rng.uniform(100_000, 7_000_000)
        elif phase_roll < 0.88:
            phase = "MARKUP"
            price_change = rng.uniform(0.02, 0.25)
            sm_flow = rng.uniform(50_000, 5_000_000)
        else:
            phase = "MARKDOWN"
            price_change = -rng.uniform(0.02, 0.20)
            sm_flow = -rng.uniform(50_000, 3_000_000)

        # Vary trader count — some tokens have weak SM activity
        traders = rng.choice([1, 2, 3, 4, 5, 7, 9, 12, 15, 18, 22, 25])
        buy_vol = max(0, sm_flow + rng.uniform(0, abs(sm_flow) * 0.5)) if sm_flow > 0 else rng.uniform(100_000, 2_000_000)
        sell_vol = max(0, -sm_flow + rng.uniform(0, abs(sm_flow) * 0.5)) if sm_flow < 0 else rng.uniform(100_000, 2_000_000)
        holdings_change = sm_flow * rng.uniform(0.3, 1.5)
        volume = (buy_vol + sell_vol) * rng.uniform(2, 8)

        # Score using real algorithm logic
        abs_flow = abs(sm_flow)
        flow_score = min(math.log10(abs_flow + 1) / math.log10(mcap), 1.0) if mcap > 1 else 0
        price_score = min(abs(price_change) * 5, 1.0)
        diversity_score = min(traders / 10, 1.0)
        conviction_score = min(abs(holdings_change) / (mcap * 0.001 + 1), 1.0) if holdings_change != 0 else 0
        strength = round(min(0.40 * flow_score + 0.25 * price_score + 0.20 * diversity_score + 0.15 * conviction_score, 1.0), 4)

        signal_count = sum([flow_score > 0.05, price_score > 0.05, diversity_score > 0.05, conviction_score > 0.05])
        if signal_count >= 3 and strength >= 0.4:
            confidence = "HIGH"
        elif signal_count >= 2 and strength >= 0.2:
            confidence = "MEDIUM"
        else:
            confidence = "LOW"

        alpha = max(0, min(100, round(strength * 100)))

        # Generate narrative
        flow_str = f"${abs_flow / 1_000_000:.1f}M" if abs_flow >= 1_000_000 else f"${abs_flow / 1_000:.0f}K"
        wallet_str = f"{traders} SM wallets"
        pct = abs(price_change * 100)
        if phase == "ACCUMULATION":
            narrative = f"{wallet_str} bought {flow_str} of {t['symbol']} while price dropped {pct:.1f}% -- stealth loading"
        elif phase == "DISTRIBUTION":
            narrative = f"{wallet_str} dumped {flow_str} of {t['symbol']} into a {pct:.1f}% rally -- exit liquidity"
        elif phase == "MARKUP":
            narrative = f"{wallet_str} added {flow_str} to {t['symbol']} confirming {pct:.1f}% uptrend"
        else:
            narrative = f"{wallet_str} sold {flow_str} of {t['symbol']} accelerating {pct:.1f}% decline"

        result = {
            "chain": t["chain"],
            "token_address": t["address"],
            "token_symbol": t["symbol"],
            "price_usd": round(price, 8),
            "price_change": round(price_change, 4),
            "market_cap": round(mcap),
            "volume_24h": round(volume),
            "market_netflow": round(sm_flow * rng.uniform(-2, 1.5)),
            "sm_net_flow": round(sm_flow),
            "sm_buy_volume": round(buy_vol),
            "sm_sell_volume": round(sell_vol),
            "sm_trader_count": traders,
            "sm_holdings_value": round(mcap * rng.uniform(0.001, 0.015)),
            "sm_holdings_change": round(holdings_change),
            "sm_wallet_labels": [],
            "divergence_strength": strength,
            "phase": phase,
            "confidence": confidence,
            "has_sm_data": True,
            "alpha_score": alpha,
            "narrative": narrative,
        }
        results.append(result)

        # Some tokens also appear in radar
        if rng.random() < 0.35:
            radar.append({
                "chain": t["chain"],
                "token_address": t["address"],
                "token_symbol": t["symbol"],
                "sm_net_flow_24h": round(sm_flow),
                "sm_net_flow_7d": round(sm_flow * rng.uniform(2, 5)),
                "sm_trader_count": traders,
                "sm_sectors": _SECTOR_MAP.get(t["symbol"], ["DeFi"]),
                "market_cap": round(mcap),
            })

    # Sort by alpha score descending
    results.sort(key=lambda r: r["alpha_score"], reverse=True)

    # Summary
    acc = sum(1 for r in results if r["phase"] == "ACCUMULATION")
    dist = sum(1 for r in results if r["phase"] == "DISTRIBUTION")
    high = sum(1 for r in results if r["confidence"] == "HIGH")
    med = sum(1 for r in results if r["confidence"] == "MEDIUM")
    low = sum(1 for r in results if r["confidence"] == "LOW")
    divergence = acc + dist

    summary = {
        "total_tokens": len(results),
        "with_sm_data": len(results),
        "sm_data_pct": 100.0,
        "sm_radar_tokens": len(radar),
        "divergence_signals": divergence,
        "accumulation": acc,
        "distribution": dist,
        "confidence_high": high,
        "confidence_medium": med,
        "confidence_low": low,
    }

    # Backtest — realistic looking stats
    total_sig = rng.randint(40, 80)
    win_rate = rng.uniform(58, 72)
    wins = round(total_sig * win_rate / 100)
    losses = total_sig - wins
    backtest = {
        "total_signals": total_sig,
        "wins": wins,
        "losses": losses,
        "win_rate": round(win_rate, 2),
        "avg_return": round(rng.uniform(5, 15), 1),
        "best_return": round(rng.uniform(25, 50), 1),
        "worst_return": round(-rng.uniform(8, 20), 1),
    }

    return {
        "results": results,
        "radar": radar,
        "summary": summary,
        "chains": chains,
        "validations": [],
        "backtest": backtest,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "demo": True,
    }
