# v4.0 Terminal Rebrand Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transform the Streamlit dashboard into a trading-terminal UI with 6 new analytical features, making it categorically different from the competitor.

**Architecture:** Rewrite `streamlit_app.py` with custom CSS injection (terminal palette, monospace headers, gradient bars), add Plotly for sparklines/heatmap/charts, add `history.py` helpers for backtesting stats, rebrand scoring to "Alpha Score" (0-100). All backend modules stay unchanged except minor additions to `history.py` and `divergence.py`.

**Tech Stack:** Streamlit, Plotly, custom CSS via `st.markdown(unsafe_allow_html=True)`, Google Fonts (JetBrains Mono)

---

### Task 1: Update theme config and add Plotly dependency

**Files:**
- Modify: `.streamlit/config.toml`
- Modify: `pyproject.toml`
- Modify: `requirements.txt`

**Step 1: Update Streamlit theme to new palette**

Replace `.streamlit/config.toml` with:
```toml
[theme]
primaryColor = "#f97316"
backgroundColor = "#0d0d0d"
secondaryBackgroundColor = "#1a1a1a"
textColor = "#d4d4d4"
font = "monospace"
```

**Step 2: Add plotly to web extras in pyproject.toml**

In `pyproject.toml`, change the web extras line to:
```toml
web = ["streamlit>=1.32.0", "plotly>=5.18.0"]
```

**Step 3: Add plotly to requirements.txt**

Append `plotly>=5.18.0` to requirements.txt.

**Step 4: Install locally**

Run: `pip install -e ".[web]"`

**Step 5: Commit**

```bash
git add .streamlit/config.toml pyproject.toml requirements.txt
git commit -m "chore: update theme to orange/amber terminal palette, add plotly dep"
```

---

### Task 2: Bump version to 4.0.0

**Files:**
- Modify: `src/nansen_divergence/__init__.py`
- Modify: `pyproject.toml`

**Step 1: Update __init__.py version**

Change `__version__ = "3.0.0"` to `__version__ = "4.0.0"` in `src/nansen_divergence/__init__.py`.

**Step 2: Update pyproject.toml version**

Change `version = "3.0.0"` to `version = "4.0.0"` in `pyproject.toml`.

**Step 3: Commit**

```bash
git add src/nansen_divergence/__init__.py pyproject.toml
git commit -m "chore: bump version to 4.0.0"
```

---

### Task 3: Add Alpha Score helper and backtesting stats to backend

**Files:**
- Modify: `src/nansen_divergence/divergence.py`
- Modify: `src/nansen_divergence/history.py`
- Create: `tests/test_alpha_score.py`

**Step 1: Write failing tests for alpha_score and backtest_stats**

Create `tests/test_alpha_score.py`:
```python
"""Tests for Alpha Score conversion and backtesting stats."""

from nansen_divergence.divergence import alpha_score
from nansen_divergence.history import backtest_stats


def test_alpha_score_converts_strength_to_0_100():
    assert alpha_score(0.0) == 0
    assert alpha_score(0.5) == 50
    assert alpha_score(1.0) == 100


def test_alpha_score_rounds_to_int():
    assert alpha_score(0.123) == 12
    assert alpha_score(0.876) == 88


def test_alpha_score_clamps():
    assert alpha_score(-0.5) == 0
    assert alpha_score(1.5) == 100


def test_backtest_stats_empty():
    result = backtest_stats([])
    assert result["total_signals"] == 0
    assert result["win_rate"] == 0.0
    assert result["avg_return"] == 0.0


def test_backtest_stats_mixed():
    validations = [
        {"phase": "ACCUMULATION", "price_change_pct": 15.0},
        {"phase": "ACCUMULATION", "price_change_pct": -5.0},
        {"phase": "DISTRIBUTION", "price_change_pct": -10.0},
        {"phase": "DISTRIBUTION", "price_change_pct": 3.0},
    ]
    result = backtest_stats(validations)
    assert result["total_signals"] == 4
    # Wins: ACC +15% (correct), DIS -10% (correct) = 2/4 = 50%
    assert result["win_rate"] == 50.0
    # ACC signals: price went up = good, price went down = bad
    # DIS signals: price went down = good, price went up = bad
    assert result["wins"] == 2
    assert result["losses"] == 2


def test_backtest_stats_best_worst():
    validations = [
        {"phase": "ACCUMULATION", "price_change_pct": 25.0},
        {"phase": "ACCUMULATION", "price_change_pct": 5.0},
        {"phase": "ACCUMULATION", "price_change_pct": -10.0},
    ]
    result = backtest_stats(validations)
    assert result["best_return"] == 25.0
    assert result["worst_return"] == -10.0
```

**Step 2: Run tests to verify they fail**

Run: `cd "C:/Users/GUDMAN/Desktop/Github files/nansen-divergence" && pytest tests/test_alpha_score.py -v`
Expected: FAIL — `ImportError: cannot import name 'alpha_score'`

**Step 3: Implement alpha_score in divergence.py**

Add at the bottom of `src/nansen_divergence/divergence.py`:
```python
def alpha_score(strength: float) -> int:
    """Convert divergence strength (0-1) to Alpha Score (0-100)."""
    return max(0, min(100, round(strength * 100)))
```

**Step 4: Implement backtest_stats in history.py**

Add at the bottom of `src/nansen_divergence/history.py`:
```python
def backtest_stats(validations: list[dict]) -> dict:
    """Compute win/loss stats from signal validations.

    A 'win' is defined as:
    - ACCUMULATION signal where price went UP (positive change)
    - DISTRIBUTION signal where price went DOWN (negative change)
    """
    if not validations:
        return {
            "total_signals": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0.0,
            "avg_return": 0.0,
            "best_return": 0.0,
            "worst_return": 0.0,
        }

    wins = 0
    returns = []

    for v in validations:
        pct = v.get("price_change_pct", 0)
        phase = v.get("phase", "")
        returns.append(pct)

        if phase == "ACCUMULATION" and pct > 0:
            wins += 1
        elif phase == "DISTRIBUTION" and pct < 0:
            wins += 1

    total = len(validations)
    return {
        "total_signals": total,
        "wins": wins,
        "losses": total - wins,
        "win_rate": round(wins / total * 100, 1) if total else 0.0,
        "avg_return": round(sum(returns) / total, 1) if total else 0.0,
        "best_return": max(returns) if returns else 0.0,
        "worst_return": min(returns) if returns else 0.0,
    }
```

**Step 5: Run tests to verify they pass**

Run: `cd "C:/Users/GUDMAN/Desktop/Github files/nansen-divergence" && pytest tests/test_alpha_score.py -v`
Expected: All 7 tests PASS

**Step 6: Run full test suite**

Run: `cd "C:/Users/GUDMAN/Desktop/Github files/nansen-divergence" && pytest tests/ -v`
Expected: All tests PASS (existing + new)

**Step 7: Commit**

```bash
git add src/nansen_divergence/divergence.py src/nansen_divergence/history.py tests/test_alpha_score.py
git commit -m "feat: add alpha_score converter and backtest_stats helper"
```

---

### Task 4: Rewrite streamlit_app.py — CSS foundation and layout skeleton

**Files:**
- Modify: `streamlit_app.py`

This task replaces the entire streamlit_app.py with the new terminal UI foundation. The file is self-contained at 270 lines currently. We rewrite it in stages.

**Step 1: Write the CSS injection and layout skeleton**

Replace `streamlit_app.py` entirely with the new terminal UI. The full file is long, so here are the key sections:

**CSS block** (injected via `st.markdown`):
```python
TERMINAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap');

/* Global overrides */
.stApp { background-color: #0d0d0d; }
h1, h2, h3 { font-family: 'JetBrains Mono', monospace !important; }
.stMetric label { font-family: 'JetBrains Mono', monospace !important; color: #737373 !important; font-size: 0.75rem !important; text-transform: uppercase !important; }
.stMetric [data-testid="stMetricValue"] { font-family: 'JetBrains Mono', monospace !important; color: #f97316 !important; }

/* Alpha score gradient bar */
.alpha-bar { height: 6px; border-radius: 3px; background: linear-gradient(90deg, #6366f1, #f97316, #f43f5e); }
.alpha-fill { height: 100%; border-radius: 3px; background: #0d0d0d; float: right; }

/* Chain pulse dot */
.chain-dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 4px; }
.chain-dot.bullish { background: #4ade80; }
.chain-dot.bearish { background: #f43f5e; }
.chain-dot.neutral { background: #737373; }

/* Phase badges */
.phase-acc { color: #4ade80; font-weight: bold; }
.phase-dis { color: #f43f5e; font-weight: bold; }
.phase-mku { color: #6366f1; font-weight: bold; }
.phase-mkd { color: #facc15; font-weight: bold; }

/* Confidence pills */
.conf-high { background: #4ade80; color: #0d0d0d; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: bold; }
.conf-med { background: #f97316; color: #0d0d0d; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: bold; }
.conf-low { background: #2a2a2a; color: #737373; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; }

/* Signal feed */
.signal-item { padding: 4px 8px; border-left: 3px solid #f97316; margin-bottom: 4px; font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; background: #1a1a1a; }
.signal-item.acc { border-left-color: #4ade80; }
.signal-item.dis { border-left-color: #f43f5e; }

/* Card surfaces */
.terminal-card { background: #1a1a1a; border: 1px solid #2a2a2a; border-radius: 8px; padding: 16px; margin-bottom: 8px; }
</style>
"""
```

**Sidebar** — same controls as v3 but with brand update:
- Title: "SM DIVERGENCE" (monospace, orange)
- Subtitle: "Smart Money vs Price — Who's Right?"
- API key, chains (checkboxes grouped in 3 cols), timeframe, limit, toggles
- Telegram config (collapsed expander)
- Scan button (orange primary)
- Auto-scan toggle + interval selector

**Main area skeleton (top to bottom):**
1. CSS injection
2. Chain Pulse Bar (HTML via `st.markdown`)
3. 6 metric cards (st.columns) — now includes Win Rate and Avg Alpha
4. Two-column section: Heatmap (left, st.plotly_chart) + Signal Feed (right, st.markdown HTML)
5. Phase token tables with inline sparklines
6. Signal Performance section with Plotly bar chart
7. SM Radar
8. Scan History

**Step 2: Verify the app loads**

Run: `cd "C:/Users/GUDMAN/Desktop/Github files/nansen-divergence" && streamlit run streamlit_app.py --server.headless true`
Expected: App starts without errors on http://localhost:8501

**Step 3: Commit**

```bash
git add streamlit_app.py
git commit -m "feat: terminal UI skeleton with CSS injection and layout zones"
```

---

### Task 5: Implement Chain Pulse Bar

**Files:**
- Modify: `streamlit_app.py` (add `render_chain_pulse()` function)

**Step 1: Add chain pulse bar renderer**

After scanning, compute per-chain phase dominance and render as HTML dots:
```python
def render_chain_pulse(results: list[dict], scanned_chains: list[str]) -> str:
    """Render chain status dots: green = accumulation dominant, red = distribution dominant, gray = not scanned."""
    chain_phases = {}
    for r in results:
        c = r.get("chain", "")
        if c not in chain_phases:
            chain_phases[c] = {"acc": 0, "dis": 0}
        if r["phase"] == "ACCUMULATION":
            chain_phases[c]["acc"] += 1
        elif r["phase"] == "DISTRIBUTION":
            chain_phases[c]["dis"] += 1

    all_chains = ["ethereum", "bnb", "solana", "base", "arbitrum", "polygon", "optimism", "avalanche", "linea"]
    chain_labels = {"ethereum": "ETH", "bnb": "BNB", "solana": "SOL", "base": "BASE", "arbitrum": "ARB",
                    "polygon": "POL", "optimism": "OP", "avalanche": "AVAX", "linea": "LNA"}

    dots = []
    for c in all_chains:
        label = chain_labels.get(c, c.upper())
        if c not in scanned_chains:
            cls = "neutral"
        elif c in chain_phases:
            p = chain_phases[c]
            cls = "bullish" if p["acc"] > p["dis"] else ("bearish" if p["dis"] > p["acc"] else "neutral")
        else:
            cls = "neutral"
        dots.append(f'<span style="margin-right:16px;"><span class="chain-dot {cls}"></span>{label}</span>')

    return f'<div style="padding:8px 0;font-family:JetBrains Mono,monospace;font-size:0.85rem;color:#d4d4d4;">{"".join(dots)}</div>'
```

Render it right below the CSS injection:
```python
if st.session_state.results is not None:
    st.markdown(render_chain_pulse(st.session_state.results, st.session_state.chains), unsafe_allow_html=True)
```

**Step 2: Test visually**

Run the app, perform a scan, verify colored dots appear.

**Step 3: Commit**

```bash
git add streamlit_app.py
git commit -m "feat: chain pulse bar with phase-dominant status dots"
```

---

### Task 6: Implement metrics row with Alpha Score and Win Rate

**Files:**
- Modify: `streamlit_app.py`

**Step 1: Update metrics row**

Replace the 6-metric row. New metrics:
```python
from nansen_divergence.divergence import alpha_score
from nansen_divergence.history import backtest_stats

# After scan completes, compute stats
validations = st.session_state.get("validations", [])
bstats = backtest_stats(validations)

cols = st.columns(6)
cols[0].metric("Tokens", summary.get("total_tokens", 0))
cols[1].metric("Divergence", summary.get("divergence_signals", 0))
cols[2].metric("Win Rate", f"{bstats['win_rate']}%" if bstats['total_signals'] > 0 else "N/A")
cols[3].metric("HIGH", summary.get("confidence_high", 0))
cols[4].metric("MEDIUM", summary.get("confidence_medium", 0))
avg_alpha = round(sum(alpha_score(r["divergence_strength"]) for r in results) / len(results)) if results else 0
cols[5].metric("Avg Alpha", avg_alpha)
```

**Step 2: Test visually**

Verify metrics show with orange monospace styling.

**Step 3: Commit**

```bash
git add streamlit_app.py
git commit -m "feat: metrics row with win rate and avg alpha score"
```

---

### Task 7: Implement Phase Heatmap

**Files:**
- Modify: `streamlit_app.py`

**Step 1: Add heatmap renderer using Plotly**

```python
import plotly.graph_objects as go

def render_heatmap(results: list[dict]) -> go.Figure:
    """Create a phase heatmap grid — tokens as cells, color by phase, opacity by strength."""
    phase_colors = {"ACCUMULATION": "#4ade80", "DISTRIBUTION": "#f43f5e", "MARKUP": "#6366f1", "MARKDOWN": "#facc15"}
    # Sort by phase then strength
    sorted_tokens = sorted(results, key=lambda x: (x["phase"], -x["divergence_strength"]))

    symbols = [t["token_symbol"] for t in sorted_tokens]
    strengths = [t["divergence_strength"] for t in sorted_tokens]
    phases = [t["phase"] for t in sorted_tokens]
    colors = [phase_colors.get(p, "#737373") for p in phases]

    # Create treemap-style chart
    fig = go.Figure(go.Treemap(
        labels=symbols,
        parents=phases,
        values=[max(s * 100, 5) for s in strengths],  # min size for visibility
        marker=dict(
            colors=colors,
            line=dict(color="#0d0d0d", width=2),
        ),
        textfont=dict(family="JetBrains Mono, monospace", size=12, color="#d4d4d4"),
        hovertemplate="<b>%{label}</b><br>Phase: %{parent}<br>Alpha: %{value:.0f}<extra></extra>",
    ))
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="#0d0d0d",
        plot_bgcolor="#0d0d0d",
        height=300,
    )
    return fig
```

Render in the left column of the two-column section.

**Step 2: Test visually**

**Step 3: Commit**

```bash
git add streamlit_app.py
git commit -m "feat: phase heatmap treemap with Plotly"
```

---

### Task 8: Implement Signal Feed

**Files:**
- Modify: `streamlit_app.py`

**Step 1: Add signal feed renderer**

Right column, shows the top HIGH/MEDIUM divergent signals as a scrolling list:
```python
def render_signal_feed(results: list[dict], max_items: int = 12) -> str:
    """Render a compact signal feed for HIGH/MEDIUM divergent tokens."""
    divergent = [r for r in results if r["phase"] in ("ACCUMULATION", "DISTRIBUTION")
                 and r["confidence"] in ("HIGH", "MEDIUM")]
    divergent.sort(key=lambda x: x["divergence_strength"], reverse=True)

    if not divergent:
        return '<div style="color:#737373;font-family:JetBrains Mono,monospace;font-size:0.85rem;">No divergence signals detected.</div>'

    items = []
    for t in divergent[:max_items]:
        cls = "acc" if t["phase"] == "ACCUMULATION" else "dis"
        sym = t["token_symbol"]
        chain = t["chain"].upper()[:3]
        alpha = alpha_score(t["divergence_strength"])
        conf_cls = "conf-high" if t["confidence"] == "HIGH" else "conf-med"
        pct = t["price_change"] * 100
        sign = "+" if pct > 0 else ""
        phase_short = "ACC" if t["phase"] == "ACCUMULATION" else "DIS"
        items.append(
            f'<div class="signal-item {cls}">'
            f'<span style="color:#d4d4d4;font-weight:bold;">{sym}</span> '
            f'<span style="color:#737373;">{chain}</span> '
            f'<span class="{conf_cls}">{phase_short}</span> '
            f'<span style="color:#f97316;">α{alpha}</span> '
            f'<span style="color:{"#4ade80" if pct > 0 else "#f43f5e"}">{sign}{pct:.1f}%</span>'
            f'</div>'
        )
    return "".join(items)
```

Render in the right column with a scrollable container.

**Step 2: Test visually**

**Step 3: Commit**

```bash
git add streamlit_app.py
git commit -m "feat: signal feed with phase-colored entries"
```

---

### Task 9: Implement sparkline mini-charts in token tables

**Files:**
- Modify: `streamlit_app.py`

**Step 1: Add sparkline generation**

Since we don't have historical price data per token (only single-point), we'll create visual divergence bars instead — showing flow direction vs price direction as opposing bars:
```python
def render_alpha_bar(strength: float) -> str:
    """Render an Alpha Score gradient bar as HTML."""
    score = alpha_score(strength)
    # Color transitions: cold (indigo) -> warm (orange) -> hot (red)
    if score >= 70:
        color = "#f43f5e"
    elif score >= 40:
        color = "#f97316"
    else:
        color = "#6366f1"
    return (
        f'<div style="display:flex;align-items:center;gap:8px;">'
        f'<div style="flex:1;height:6px;background:#2a2a2a;border-radius:3px;overflow:hidden;">'
        f'<div style="width:{score}%;height:100%;background:{color};border-radius:3px;"></div>'
        f'</div>'
        f'<span style="font-family:JetBrains Mono,monospace;font-size:0.8rem;color:{color};font-weight:bold;">{score}</span>'
        f'</div>'
    )
```

Replace the dataframe-based token tables with custom HTML tables that include:
- Symbol + NEW badge
- Chain
- Price change (colored)
- Net Flow (formatted USD)
- Alpha bar (gradient)
- Confidence pill (HTML badge)
- DexScreener link
- Narrative (muted italic below row)

**Step 2: Test visually**

**Step 3: Commit**

```bash
git add streamlit_app.py
git commit -m "feat: custom HTML token tables with alpha bars and confidence pills"
```

---

### Task 10: Implement Signal Performance (Backtesting) section

**Files:**
- Modify: `streamlit_app.py`

**Step 1: Add backtesting section**

After the phase tables, render a performance section:
```python
def render_performance(bstats: dict, validations: list[dict]):
    """Render signal performance section with stats + Plotly chart."""
    if bstats["total_signals"] == 0:
        st.info("No historical signals to validate yet. Scan regularly to build signal history.")
        return

    # Stat cards
    cols = st.columns(4)
    cols[0].metric("Win Rate", f"{bstats['win_rate']}%")
    cols[1].metric("Avg Return", f"{bstats['avg_return']:+.1f}%")
    cols[2].metric("Best", f"{bstats['best_return']:+.1f}%")
    cols[3].metric("Worst", f"{bstats['worst_return']:+.1f}%")

    # Outcome chart
    if validations:
        import plotly.graph_objects as go

        symbols = [v["token_symbol"] for v in validations[:20]]
        returns = [v["price_change_pct"] for v in validations[:20]]
        colors = ["#4ade80" if r > 0 else "#f43f5e" for r in returns]

        fig = go.Figure(go.Bar(
            x=symbols, y=returns,
            marker_color=colors,
            text=[f"{r:+.1f}%" for r in returns],
            textposition="outside",
            textfont=dict(family="JetBrains Mono, monospace", size=10, color="#d4d4d4"),
        ))
        fig.update_layout(
            paper_bgcolor="#0d0d0d",
            plot_bgcolor="#1a1a1a",
            font=dict(family="JetBrains Mono, monospace", color="#d4d4d4"),
            xaxis=dict(gridcolor="#2a2a2a"),
            yaxis=dict(gridcolor="#2a2a2a", title="Return %"),
            margin=dict(l=40, r=20, t=20, b=40),
            height=250,
        )
        st.plotly_chart(fig, use_container_width=True)
```

**Step 2: Test visually**

**Step 3: Commit**

```bash
git add streamlit_app.py
git commit -m "feat: signal performance backtesting section with win rate and Plotly chart"
```

---

### Task 11: Implement Token Deep-Dive Drawer

**Files:**
- Modify: `streamlit_app.py`

**Step 1: Add inline deep-dive expander**

Inside each token row in the phase tables, add a clickable expander that fetches and shows deep-dive data:
```python
def render_deep_dive(token: dict):
    """Render inline deep-dive for a token using existing deep_dive module."""
    from nansen_divergence.deep_dive import deep_dive_token

    chain = token.get("chain", "")
    addr = token.get("token_address", "")

    with st.spinner(f"Deep diving {token['token_symbol']}..."):
        try:
            data = deep_dive_token(chain, addr, days=7, top_wallets=3)
        except Exception as e:
            st.error(f"Deep dive failed: {e}")
            return

    if not data:
        st.warning("No deep dive data available.")
        return

    cols = st.columns(3)

    # Flow Intelligence
    flow_intel = data.get("flow_intelligence", {})
    if flow_intel:
        cols[0].markdown("**Flow Intelligence**")
        for label, val in flow_intel.items():
            if val and isinstance(val, (int, float)):
                cols[0].markdown(f"`{label}`: {_fmt_usd(val)}")

    # Nansen Score
    indicators = data.get("indicators", {})
    if indicators:
        cols[1].markdown("**Nansen Score**")
        ns = indicators.get("nansen_score")
        if ns is not None:
            cols[1].metric("Score", f"{ns}/100")

    # Top Wallets
    wallets = data.get("wallets", [])
    if wallets:
        cols[2].markdown("**Top SM Wallets**")
        for w in wallets[:3]:
            lbl = w.get("label", "Unknown")
            pnl = w.get("realized_pnl", 0)
            cols[2].markdown(f"`{lbl}` — PnL: {_fmt_usd(pnl)}")
```

Each token row gets a `st.expander` containing this deep-dive. The deep-dive button is optional (requires API credits).

**Step 2: Test visually**

**Step 3: Commit**

```bash
git add streamlit_app.py
git commit -m "feat: inline token deep-dive drawer with flow intel and wallet profiles"
```

---

### Task 12: Add auto-scan mode

**Files:**
- Modify: `streamlit_app.py`

**Step 1: Add auto-scan toggle to sidebar**

```python
# In sidebar section:
st.divider()
auto_scan = st.toggle("Auto-scan", value=False, help="Re-scan automatically at set interval")
scan_interval = st.selectbox("Interval", [1, 2, 5, 10, 15], index=2, disabled=not auto_scan, format_func=lambda x: f"{x} min")

# In main area, after initial scan logic:
if auto_scan and st.session_state.results is not None:
    import time
    time.sleep(scan_interval * 60)
    st.rerun()
```

Note: Streamlit's `st.rerun()` handles the loop. The sleep runs server-side between reruns.

**Step 2: Test by enabling auto-scan and watching for rerun**

**Step 3: Commit**

```bash
git add streamlit_app.py
git commit -m "feat: auto-scan mode with configurable interval"
```

---

### Task 13: Final integration, lint, and test

**Files:**
- Modify: `streamlit_app.py` (final polish)

**Step 1: Run ruff lint**

Run: `cd "C:/Users/GUDMAN/Desktop/Github files/nansen-divergence" && ruff check . --fix && ruff format .`
Expected: Clean or auto-fixed

**Step 2: Run full test suite**

Run: `cd "C:/Users/GUDMAN/Desktop/Github files/nansen-divergence" && pytest tests/ -v`
Expected: All tests pass (53 existing + 7 new = 60)

**Step 3: Test Streamlit app end-to-end**

Run: `streamlit run streamlit_app.py`
Verify:
- [ ] Dark terminal theme loads (black bg, orange accents, monospace headers)
- [ ] Chain pulse bar shows colored dots after scan
- [ ] Metrics row includes Win Rate and Avg Alpha
- [ ] Phase heatmap treemap renders
- [ ] Signal feed shows HIGH/MEDIUM divergent tokens
- [ ] Token tables have Alpha bars, confidence pills, DexScreener links
- [ ] Signal Performance section shows backtest stats + chart
- [ ] Deep-dive expanders work (if API credits available)
- [ ] SM Radar section renders
- [ ] Auto-scan toggle works
- [ ] Scan history loads

**Step 4: Commit**

```bash
git add -A
git commit -m "v4.0.0: terminal UI rebrand — heatmap, alpha score, backtesting, chain pulse, signal feed"
```

---

### Task 14: Update README

**Files:**
- Modify: `README.md`

**Step 1: Update README header and What's New section**

Update version to 4.0, add v4.0 section:
- Terminal UI rebrand (orange/amber, monospace, trading terminal aesthetic)
- Phase Heatmap (visual grid of all tokens by phase)
- Alpha Score (proprietary 0-100 scoring)
- Signal Performance (win rate, avg return, outcome chart)
- Chain Pulse Bar (cross-chain phase dominance at a glance)
- Signal Feed (live scrolling divergence signals)
- Auto-scan mode
- Inline deep-dive drawers

**Step 2: Commit and push**

```bash
git add README.md
git commit -m "docs: update README for v4.0.0 terminal rebrand"
```
