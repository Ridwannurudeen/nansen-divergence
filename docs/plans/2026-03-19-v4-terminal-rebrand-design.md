# v4.0 Terminal Rebrand Design

## Goal
Differentiate from competitor (smart-money-divergence-dectector.streamlit.app) by transforming the Streamlit dashboard into a trading terminal experience with unique analytical features impossible to replicate without our scoring engine, signal history, and multi-source pipeline.

## Visual Identity

### Color Palette (Orange/Amber Aggressive)
| Role | Hex | Usage |
|------|-----|-------|
| Background | `#0d0d0d` | Page background, true black |
| Surface | `#1a1a1a` | Cards, panels, elevated surfaces |
| Border | `#2a2a2a` | Subtle grid lines, card borders |
| Accent | `#f97316` | Links, active states, headers, brand color |
| Secondary | `#fb923c` | Hover states, secondary highlights |
| Bullish | `#4ade80` | ACCUMULATION phase, positive flows, price up |
| Bearish | `#f43f5e` | DISTRIBUTION phase, negative flows, price down |
| Warning | `#facc15` | MARKDOWN phase, caution states |
| Neutral | `#6366f1` | MARKUP phase, confirmed trends |
| Text | `#d4d4d4` | Primary text |
| Text muted | `#737373` | Labels, secondary info |

### Typography
- Headers: `JetBrains Mono` (Google Fonts) → `Fira Code` → `monospace`
- Body: system sans-serif
- Data/numbers: monospace (column alignment)

## New Features (6)

### 1. Phase Heatmap Grid
Visual grid where each token = colored cell. Color = Wyckoff phase, opacity = strength, size = market cap tier. Implemented via Plotly heatmap or custom HTML grid via `st.components.v1.html()`.

### 2. Sparkline Charts
Inline Plotly mini-charts per token showing price trend vs SM flow trend. Two lines diverging visually = the signal. Renders inside expanded phase sections.

### 3. Signal Performance Tracker (Backtesting)
Uses existing `history.py` validate_signals(). Shows: win rate %, avg return, best/worst call, signal count. Displayed as metric cards + Plotly bar chart of outcomes.

### 4. Alpha Score (Rebrand)
Rename `divergence_strength` (0-1) to Alpha Score (0-100). Display with gradient bar: cold (blue/gray) → warm (orange) → hot (red). Proprietary branding.

### 5. Chain Pulse Bar
Top of main area: 9 chain icons with colored status dots. Green = accumulation dominant, red = distribution dominant, gray = not scanned. Shows cross-chain positioning at a glance.

### 6. Token Deep-Dive Drawer
Click token row → expander opens inline with flow intelligence breakdown, wallet labels, Nansen Score. No page navigation needed. Uses existing `deep_dive.py`.

## Layout Structure

```
SIDEBAR:                    MAIN AREA:
┌──────────────┐            ┌────────────────────────────────┐
│ Brand + ver  │            │ CHAIN PULSE BAR                │
│ API Key      │            │ [ETH●] [SOL●] [BNB○] ...      │
│ Chains       │            ├────────────────────────────────┤
│ Timeframe    │            │ METRICS ROW (6 cards)          │
│ Limit        │            │ Tokens | Signals | Win Rate    │
│ Toggles      │            │ HIGH | MEDIUM | Avg Alpha      │
│ Telegram     │            ├─────────────┬──────────────────┤
│ [SCAN btn]   │            │ HEATMAP     │ SIGNAL FEED      │
│ [Auto-scan]  │            │ (grid)      │ (scrolling list) │
└──────────────┘            ├─────────────┴──────────────────┤
                            │ TOKEN TABLES (by phase)        │
                            │ + inline sparklines            │
                            │ + deep-dive drawers            │
                            ├────────────────────────────────┤
                            │ SIGNAL PERFORMANCE             │
                            │ (backtesting stats + chart)    │
                            ├────────────────────────────────┤
                            │ SM RADAR                       │
                            ├────────────────────────────────┤
                            │ SCAN HISTORY                   │
                            └────────────────────────────────┘
```

## Versioning
This ships as v4.0.0. Bumps from v3.0.0.

## Tech Stack
- Streamlit (stay on current platform)
- Plotly (sparklines, heatmap, performance charts)
- Custom CSS injection via `st.markdown(unsafe_allow_html=True)`
- Google Fonts (JetBrains Mono)
- Existing backend: scanner.py, divergence.py, history.py, deep_dive.py

## What the Competitor Cannot Copy
1. Wyckoff phase classification (4 phases vs binary divergence)
2. Log-scaled multi-factor scoring (their weights are linear 40/30/20/10)
3. Signal validation / backtesting (they have no history layer)
4. SM Radar (tokens outside screener)
5. Narrative generation (one-liner explanations)
6. New token detection (first-seen flagging)
7. Deep-dive integration (flow intel + wallet profiling)
