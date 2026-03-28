import Link from "next/link";
import { LayoutDashboard, Radar, TrendingUp, ArrowRightLeft, Search } from "lucide-react";

const FEATURES = [
  {
    icon: LayoutDashboard,
    title: "Dashboard",
    href: "/",
    desc: "Real-time divergence heat map, signal feed, and metric cards. Tokens colored by Wyckoff phase, sized by market cap.",
  },
  {
    icon: Radar,
    title: "Pre-Breakout Radar",
    href: "/radar",
    desc: "High volume-activity tokens showing divergent signals. Catch institutional positioning before the crowd.",
  },
  {
    icon: TrendingUp,
    title: "Signal Performance",
    href: "/performance",
    desc: "Track historical signal outcomes with win rates, return distributions, and timeline visualization.",
  },
  {
    icon: ArrowRightLeft,
    title: "Cross-Chain Flows",
    href: "/flows",
    desc: "Chain momentum scores, sector rotation, and volume flow aggregation across 8 blockchains.",
  },
  {
    icon: Search,
    title: "Token Deep Dive",
    href: "/",
    desc: "Click any token for full intelligence: flow by wallet type, buyers/sellers, Nansen Score, and wallet profiles.",
  },
];

export default function About() {
  return (
    <main className="max-w-4xl mx-auto px-4 py-8">
      <h1 className="text-3xl font-mono font-bold text-accent glow-orange mb-2">How It Works</h1>
      <p className="text-muted mb-8">Multi-chain divergence scanner with volume proxy analysis and Wyckoff phase classification</p>

      <section className="mb-8">
        <h2 className="text-xl font-mono font-bold text-white mb-3">Wyckoff Phases</h2>
        <div className="bg-surface border border-border rounded-lg overflow-hidden">
          <table className="w-full text-sm font-mono">
            <thead><tr className="border-b border-border text-muted">
              <th className="text-left p-3">Phase</th><th className="p-3">SM Flow</th><th className="p-3">Price</th><th className="text-left p-3">Signal</th>
            </tr></thead>
            <tbody>
              <tr className="border-b border-border/50"><td className="p-3 text-bullish font-bold">ACCUMULATION</td><td className="p-3 text-center">Buying</td><td className="p-3 text-center">Falling</td><td className="p-3">Bullish divergence — SM buying the dip</td></tr>
              <tr className="border-b border-border/50"><td className="p-3 text-bearish font-bold">DISTRIBUTION</td><td className="p-3 text-center">Selling</td><td className="p-3 text-center">Rising</td><td className="p-3">Bearish divergence — SM exiting into strength</td></tr>
              <tr className="border-b border-border/50"><td className="p-3 text-neutral font-bold">MARKUP</td><td className="p-3 text-center">Buying</td><td className="p-3 text-center">Rising</td><td className="p-3">Trend confirmed — momentum aligned</td></tr>
              <tr><td className="p-3 text-warning font-bold">MARKDOWN</td><td className="p-3 text-center">Selling</td><td className="p-3 text-center">Falling</td><td className="p-3">Capitulation — both SM and price declining</td></tr>
            </tbody>
          </table>
        </div>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-mono font-bold text-white mb-3">Features</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {FEATURES.map(({ icon: Icon, title, href, desc }) => (
            <Link key={title} href={href} className="bg-surface border border-border rounded-lg p-4 hover:border-accent/50 transition-colors group">
              <div className="flex items-center gap-2 mb-2">
                <Icon size={16} className="text-accent" />
                <h3 className="font-mono font-bold text-white group-hover:text-accent transition-colors">{title}</h3>
              </div>
              <p className="text-sm text-muted leading-relaxed">{desc}</p>
            </Link>
          ))}
        </div>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-mono font-bold text-white mb-3">Alpha Score</h2>
        <p className="text-muted leading-relaxed">
          Each token gets an Alpha Score (0-100) based on four weighted factors:
          flow magnitude (40%), price movement (25%), wallet diversity (20%), and holdings conviction (15%).
          Scores use log-scaled normalization to prevent large-cap tokens from dominating.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-mono font-bold text-white mb-3">Data Pipeline</h2>
        <div className="bg-surface border border-border rounded-lg p-4 font-mono text-sm space-y-2">
          <div className="flex items-center gap-2">
            <span className="text-accent">1.</span>
            <span className="text-muted">MCP Discovery</span>
            <span className="text-muted/50">—</span>
            <span className="text-white">Token search across 8 chains via Nansen MCP (0 credits)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-accent">2.</span>
            <span className="text-bullish font-bold">CLI Enrichment</span>
            <span className="text-muted/50">—</span>
            <span className="text-white">Real SM data via <code className="text-accent">token screener</code> + <code className="text-accent">smart-money netflow</code> (~12 credits/cycle)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-accent">3.</span>
            <span className="text-muted">Price History</span>
            <span className="text-muted/50">—</span>
            <span className="text-white">SQLite-tracked price snapshots for real change computation</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-accent">4.</span>
            <span className="text-muted">Volume Proxy</span>
            <span className="text-muted/50">—</span>
            <span className="text-white">Vol/MCap ratio + relative volume → activity classification</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-accent">5.</span>
            <span className="text-muted">Divergence Engine</span>
            <span className="text-muted/50">—</span>
            <span className="text-white">Price-volume divergence → Wyckoff phase + confidence</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-accent">6.</span>
            <span className="text-muted">Signal History</span>
            <span className="text-muted/50">—</span>
            <span className="text-white">Outcome tracking + backtesting against price changes</span>
          </div>
        </div>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-mono font-bold text-white mb-3">Hybrid Pipeline: CLI + Volume Proxy</h2>
        <p className="text-muted leading-relaxed mb-3">
          Top tokens on Ethereum and BNB Chain are enriched with real smart money data from the Nansen CLI
          (<code className="text-accent">research token screener</code> + <code className="text-accent">research smart-money netflow</code>).
          Remaining tokens use volume proxy analysis. Tokens with CLI data are marked with a green
          <span className="text-xs bg-bullish text-bg px-1 rounded font-bold mx-1">CLI</span> badge;
          volume-proxy tokens show a gray <span className="text-xs bg-border text-muted px-1 rounded mx-1">VP</span> badge.
        </p>
        <div className="bg-surface border border-border rounded-lg overflow-hidden">
          <table className="w-full text-sm font-mono">
            <thead><tr className="border-b border-border text-muted">
              <th className="text-left p-3">CLI Command</th><th className="text-left p-3">Data</th><th className="text-right p-3">Credits</th>
            </tr></thead>
            <tbody>
              <tr className="border-b border-border/50">
                <td className="p-3 text-accent">research token screener</td>
                <td className="p-3 text-white">Real price, market cap, market netflow</td>
                <td className="p-3 text-right text-muted">1/page</td>
              </tr>
              <tr>
                <td className="p-3 text-accent">research smart-money netflow</td>
                <td className="p-3 text-white">Real SM net flow per token (24h/7d)</td>
                <td className="p-3 text-right text-muted">5/page</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p className="text-muted text-sm mt-2">
          Enrichment runs every 30 minutes, consuming ~12 credits per cycle (~288/day). Configurable via
          <code className="text-accent ml-1">CLI_ENRICH_CHAINS</code> and <code className="text-accent ml-1">CLI_ENRICH_MINUTES</code> env vars.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-mono font-bold text-white mb-3">Volume Proxy Methodology</h2>
        <p className="text-muted leading-relaxed mb-3">
          Instead of requiring premium smart money wallet data, the scanner derives institutional activity signals from publicly available volume and price data:
        </p>
        <div className="bg-surface border border-border rounded-lg overflow-hidden">
          <table className="w-full text-sm font-mono">
            <thead><tr className="border-b border-border text-muted">
              <th className="text-left p-3">Metric</th><th className="text-left p-3">Formula</th><th className="text-left p-3">What It Detects</th>
            </tr></thead>
            <tbody>
              <tr className="border-b border-border/50"><td className="p-3 text-accent font-bold">Vol/MCap Ratio</td><td className="p-3 text-white">volume_24h / market_cap</td><td className="p-3 text-muted">Unusual trading activity relative to token size</td></tr>
              <tr className="border-b border-border/50"><td className="p-3 text-accent font-bold">Relative Volume</td><td className="p-3 text-white">current_vol / avg_vol_72h</td><td className="p-3 text-muted">Volume spikes vs recent baseline</td></tr>
              <tr className="border-b border-border/50"><td className="p-3 text-accent font-bold">Price-Vol Divergence</td><td className="p-3 text-white">high_volume + falling_price</td><td className="p-3 text-muted">Accumulation (buying into weakness)</td></tr>
              <tr><td className="p-3 text-accent font-bold">Whale Count Est.</td><td className="p-3 text-white">volume / avg_institutional_trade</td><td className="p-3 text-muted">Estimated number of large transactions</td></tr>
            </tbody>
          </table>
        </div>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-mono font-bold text-white mb-3">Try It Yourself</h2>
        <p className="text-muted leading-relaxed mb-3">
          Install the Nansen CLI and run these commands to see the raw data this scanner uses:
        </p>
        <div className="bg-bg border border-border rounded-lg p-4 font-mono text-sm space-y-3">
          <div>
            <div className="text-muted text-xs mb-1"># Install Nansen CLI</div>
            <code className="text-bullish">npm i -g nansen-cli && nansen login</code>
          </div>
          <div>
            <div className="text-muted text-xs mb-1"># Token screener — top tokens by volume (1 credit)</div>
            <code className="text-accent">nansen research token screener --chain ethereum --timeframe 24h</code>
          </div>
          <div>
            <div className="text-muted text-xs mb-1"># Smart money net flow — where SM wallets are moving (5 credits)</div>
            <code className="text-accent">nansen research smart-money netflow --chain ethereum</code>
          </div>
          <div>
            <div className="text-muted text-xs mb-1"># SM dex trades — individual whale trades (5 credits)</div>
            <code className="text-accent">nansen research smart-money dex-trades --chain bnb</code>
          </div>
          <div>
            <div className="text-muted text-xs mb-1"># Token deep dive — flow intelligence + Nansen Score (5 credits)</div>
            <code className="text-accent">nansen research token flow-intelligence --chain ethereum --token 0x...</code>
          </div>
          <div>
            <div className="text-muted text-xs mb-1"># Wallet profiler — who is this wallet? (1 credit)</div>
            <code className="text-accent">nansen research profiler labels --address 0x... --chain ethereum</code>
          </div>
        </div>
        <p className="text-muted text-sm mt-2">
          All 9 Nansen CLI endpoints are integrated. The scanner runs <code className="text-accent">token screener</code> +
          <code className="text-accent">smart-money netflow</code> every 30 minutes for ETH/BNB enrichment, plus
          <code className="text-accent">flow-intelligence</code>, <code className="text-accent">who-bought-sold</code>, and
          <code className="text-accent">token indicators</code> for top token deep dives.
        </p>
      </section>

      <section>
        <h2 className="text-xl font-mono font-bold text-white mb-3">Coverage</h2>
        <p className="text-muted leading-relaxed">
          Scans 8 blockchains (Ethereum, BNB, Solana, Base, Arbitrum, Polygon, Optimism, Avalanche)
          via Nansen MCP discovery at zero credit cost. Auto-refreshed every 5 minutes.
          Signal outcomes tracked in SQLite and validated against subsequent price movements for backtesting.
        </p>
      </section>
    </main>
  );
}
