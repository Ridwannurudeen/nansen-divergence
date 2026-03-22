export default function About() {
  return (
    <main className="max-w-4xl mx-auto px-4 py-8">
      <h1 className="text-3xl font-mono font-bold text-accent mb-6">How It Works</h1>

      <section className="mb-8">
        <h2 className="text-xl font-mono font-bold text-white mb-3">Wyckoff Phases</h2>
        <div className="bg-surface border border-border rounded-lg overflow-hidden">
          <table className="w-full text-sm font-mono">
            <thead><tr className="border-b border-border text-muted">
              <th className="text-left p-3">Phase</th><th className="p-3">SM Flow</th><th className="p-3">Price</th><th className="text-left p-3">Signal</th>
            </tr></thead>
            <tbody>
              <tr className="border-b border-border/50"><td className="p-3 text-bullish font-bold">ACCUMULATION</td><td className="p-3 text-center">Buying</td><td className="p-3 text-center">Falling</td><td className="p-3">Bullish divergence</td></tr>
              <tr className="border-b border-border/50"><td className="p-3 text-bearish font-bold">DISTRIBUTION</td><td className="p-3 text-center">Selling</td><td className="p-3 text-center">Rising</td><td className="p-3">Bearish divergence</td></tr>
              <tr className="border-b border-border/50"><td className="p-3 text-neutral font-bold">MARKUP</td><td className="p-3 text-center">Buying</td><td className="p-3 text-center">Rising</td><td className="p-3">Trend confirmed</td></tr>
              <tr><td className="p-3 text-warning font-bold">MARKDOWN</td><td className="p-3 text-center">Selling</td><td className="p-3 text-center">Falling</td><td className="p-3">Capitulation</td></tr>
            </tbody>
          </table>
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

      <section>
        <h2 className="text-xl font-mono font-bold text-white mb-3">Data Sources</h2>
        <p className="text-muted leading-relaxed">
          Scans 9 blockchains using Nansen&apos;s smart money data: token screener, SM dex-trades,
          SM holdings, and SM netflow. Results are cached and auto-refreshed every 30 minutes.
        </p>
      </section>
    </main>
  );
}
