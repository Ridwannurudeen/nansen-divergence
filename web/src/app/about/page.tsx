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
    desc: "SM-only tokens not yet in mainstream screener results. Catch smart money positioning before the crowd.",
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
    desc: "Chain momentum scores, sector rotation, and SM capital flow aggregation across 9 blockchains.",
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
      <p className="text-muted mb-8">Multi-chain smart money divergence scanner with Wyckoff phase classification</p>

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
            <span className="text-muted">Token Screener</span>
            <span className="text-muted/50">—</span>
            <span className="text-white">Price, market cap, volume, market netflow</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-accent">2.</span>
            <span className="text-muted">SM Dex-Trades</span>
            <span className="text-muted/50">—</span>
            <span className="text-white">Individual wallet trades aggregated per token</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-accent">3.</span>
            <span className="text-muted">SM Holdings</span>
            <span className="text-muted/50">—</span>
            <span className="text-white">Position values + 24h balance changes</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-accent">4.</span>
            <span className="text-muted">SM Netflow</span>
            <span className="text-muted/50">—</span>
            <span className="text-white">Pre-breakout radar tokens</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-accent">5.</span>
            <span className="text-muted">Deep Dive</span>
            <span className="text-muted/50">—</span>
            <span className="text-white">Flow intelligence, buyers/sellers, wallet profiles</span>
          </div>
        </div>
      </section>

      <section>
        <h2 className="text-xl font-mono font-bold text-white mb-3">Coverage</h2>
        <p className="text-muted leading-relaxed">
          Scans 9 blockchains (Ethereum, BNB, Solana, Base, Arbitrum, Polygon, Optimism, Avalanche, Linea)
          using Nansen&apos;s smart money data. Results cached and auto-refreshed every 30 minutes.
          Signal outcomes validated against current prices for backtesting.
        </p>
      </section>
    </main>
  );
}
