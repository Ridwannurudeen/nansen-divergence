"use client";

import useSWR from "swr";
import { useState, useEffect, useCallback } from "react";
import { Star } from "lucide-react";
import { ScanData } from "@/lib/types";
import { fetcher } from "@/lib/api";
import { getWatchlist } from "@/lib/watchlist";
import { Header } from "@/components/Header";
import { ChainPulse } from "@/components/ChainPulse";
import { MetricCards } from "@/components/MetricCards";
import { SignalFeed } from "@/components/SignalFeed";
import { TokenTable } from "@/components/TokenTable";
import { HeatMap } from "@/components/HeatMap";

function SkeletonPulse({ className }: { className?: string }) {
  return <div className={`animate-pulse bg-surface rounded ${className}`} />;
}

function DashboardSkeleton() {
  return (
    <div className="space-y-4">
      {/* Chain pulse skeleton */}
      <div className="flex gap-3 py-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <SkeletonPulse key={i} className="h-8 w-16" />
        ))}
      </div>
      {/* Metric cards skeleton */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <SkeletonPulse key={i} className="h-24" />
        ))}
      </div>
      {/* HeatMap skeleton */}
      <SkeletonPulse className="h-20" />
      {/* Signal + Radar skeleton */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <SkeletonPulse key={i} className="h-14" />
          ))}
        </div>
        <SkeletonPulse className="h-72" />
      </div>
      {/* Token table skeleton */}
      <div className="space-y-2">
        <div className="flex gap-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <SkeletonPulse key={i} className="h-8 w-28" />
          ))}
        </div>
        {Array.from({ length: 6 }).map((_, i) => (
          <SkeletonPulse key={i} className="h-10" />
        ))}
      </div>
    </div>
  );
}

export default function Home() {
  const { data, error, isLoading } = useSWR<ScanData>("/api/scan/latest", fetcher, {
    refreshInterval: 60000,
  });
  const { data: sparklineData } = useSWR<{ sparklines: Record<string, number[]> }>(
    "/api/history/sparklines?days=7&points=10",
    fetcher,
    { refreshInterval: 60000 }
  );
  const { data: streakData } = useSWR<{ streaks: Record<string, { phase: string; streak: number; since: string }> }>(
    "/api/history/streaks?days=14",
    fetcher,
    { refreshInterval: 60000 }
  );
  const [activeChain, setActiveChain] = useState<string | null>(null);

  const filteredResults = data?.results
    ? activeChain
      ? data.results.filter((r) => r.chain === activeChain)
      : data.results
    : [];

  const avgAlpha = filteredResults.length > 0
    ? Math.round(filteredResults.reduce((sum, r) => sum + (r.alpha_score || 0), 0) / filteredResults.length)
    : 0;

  const [watchlist, setWatchlist] = useState<string[]>([]);
  useEffect(() => {
    setWatchlist(getWatchlist());
    const handler = () => setWatchlist(getWatchlist());
    window.addEventListener("watchlist-change", handler);
    return () => window.removeEventListener("watchlist-change", handler);
  }, []);

  const watchedTokens = filteredResults.filter(
    (r) => watchlist.includes(r.token_address.toLowerCase())
  );

  return (
    <main className="max-w-7xl mx-auto px-4 py-4">
      <Header timestamp={data?.timestamp} />

      {isLoading && <DashboardSkeleton />}

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

          <HeatMap results={filteredResults} />

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 py-4">
            <div className="lg:col-span-2">
              <h2 className="font-mono font-bold text-sm text-muted mb-2">SIGNAL FEED</h2>
              <SignalFeed results={filteredResults} streaks={streakData?.streaks} />
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

          {watchedTokens.length > 0 && (
            <div className="mb-4">
              <h2 className="font-mono font-bold text-sm text-muted mb-2 flex items-center gap-1.5">
                <Star size={14} className="text-accent" fill="#f97316" />
                WATCHLIST ({watchedTokens.length})
              </h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
                {watchedTokens.map((t) => (
                  <div key={`watch-${t.chain}-${t.token_address}`} className="bg-surface border border-accent/30 rounded-lg p-3 font-mono text-xs">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-white font-bold">{t.token_symbol}</span>
                      <span className="text-muted">{t.chain.toUpperCase()}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className={t.price_change > 0 ? "text-bullish" : "text-bearish"}>
                        {t.price_change > 0 ? "+" : ""}{(t.price_change * 100).toFixed(1)}%
                      </span>
                      <span className={`px-1.5 py-0.5 rounded text-xs font-bold ${
                        t.phase === "ACCUMULATION" ? "bg-bullish/20 text-bullish" :
                        t.phase === "DISTRIBUTION" ? "bg-bearish/20 text-bearish" :
                        "bg-border text-muted"
                      }`}>{t.phase}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          <TokenTable results={filteredResults} sparklines={sparklineData?.sparklines} />
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
