"use client";

import useSWR from "swr";
import { useState } from "react";
import { ScanData } from "@/lib/types";
import { fetcher } from "@/lib/api";
import { Header } from "@/components/Header";
import { ChainPulse } from "@/components/ChainPulse";
import { MetricCards } from "@/components/MetricCards";
import { SignalFeed } from "@/components/SignalFeed";
import { TokenTable } from "@/components/TokenTable";

export default function Home() {
  const { data, error, isLoading } = useSWR<ScanData>("/api/scan/latest", fetcher, {
    refreshInterval: 60000,
  });
  const [activeChain, setActiveChain] = useState<string | null>(null);

  const filteredResults = data?.results
    ? activeChain
      ? data.results.filter((r) => r.chain === activeChain)
      : data.results
    : [];

  const avgAlpha = filteredResults.length > 0
    ? Math.round(filteredResults.reduce((sum, r) => sum + (r.alpha_score || 0), 0) / filteredResults.length)
    : 0;

  return (
    <main className="max-w-7xl mx-auto px-4 py-4">
      <Header timestamp={data?.timestamp} />

      {isLoading && (
        <div className="flex items-center justify-center py-20">
          <div className="text-accent font-mono animate-pulse">Loading scan data...</div>
        </div>
      )}

      {error && (
        <div className="bg-surface border border-bearish rounded-lg p-4 my-4 font-mono text-sm text-bearish">
          Failed to load scan data. The API may still be running its first scan.
        </div>
      )}

      {data && (
        <>
          <ChainPulse
            results={data.results}
            scannedChains={data.chains}
            activeChain={activeChain}
            onChainClick={setActiveChain}
          />

          <MetricCards
            summary={data.summary}
            backtest={data.backtest || { total_signals: 0, wins: 0, losses: 0, win_rate: 0, avg_return: 0, best_return: 0, worst_return: 0 }}
            avgAlpha={avgAlpha}
          />

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 py-4">
            <div className="lg:col-span-2">
              <h2 className="font-mono font-bold text-sm text-muted mb-2">SIGNAL FEED</h2>
              <SignalFeed results={filteredResults} />
            </div>
            <div>
              <h2 className="font-mono font-bold text-sm text-muted mb-2">SM RADAR</h2>
              <div className="bg-surface border border-border rounded-lg p-3 max-h-[420px] overflow-y-auto">
                {data.radar && data.radar.length > 0 ? (
                  <div className="space-y-1 text-xs font-mono">
                    {data.radar.slice(0, 15).map((r, i) => (
                      <div key={i} className="flex justify-between py-1 border-b border-border/50">
                        <span className="text-white">{r.token_symbol}</span>
                        <span className="text-muted">{r.chain.slice(0, 3).toUpperCase()}</span>
                        <span className={r.sm_net_flow_24h > 0 ? "text-bullish" : "text-bearish"}>
                          {r.sm_net_flow_24h > 0 ? "+" : ""}{(r.sm_net_flow_24h / 1e6).toFixed(1)}M
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-muted text-sm">No radar data yet.</div>
                )}
              </div>
            </div>
          </div>

          <TokenTable results={filteredResults} />
        </>
      )}

      {!isLoading && !error && !data && (
        <div className="text-center py-20">
          <h2 className="text-2xl font-mono font-bold text-accent mb-4">SM DIVERGENCE</h2>
          <p className="text-muted">Waiting for first scan to complete...</p>
          <p className="text-muted text-sm mt-2">The scanner runs automatically every 30 minutes.</p>
        </div>
      )}
    </main>
  );
}
