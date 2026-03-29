"use client";

import useSWR from "swr";
import { useState, useEffect } from "react";
import { Star, Key } from "lucide-react";
import { ScanData } from "@/lib/types";
import { fetcher } from "@/lib/api";
import { getWatchlist } from "@/lib/watchlist";
import { getApiKey } from "@/lib/settings";
import { Header } from "@/components/Header";
import { ChainPulse } from "@/components/ChainPulse";
import { MetricCards } from "@/components/MetricCards";
import { SignalFeed } from "@/components/SignalFeed";
import { TokenTable } from "@/components/TokenTable";
import { HeatMap } from "@/components/HeatMap";
import { CLIActivity } from "@/components/CLIActivity";

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

function ByokBanner() {
  const [hasKey, setHasKey] = useState(() => !!getApiKey());
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    const handler = () => setHasKey(!!getApiKey());
    window.addEventListener("apikey-change", handler);
    return () => window.removeEventListener("apikey-change", handler);
  }, []);

  if (hasKey || dismissed) return null;

  return (
    <div className="bg-accent/5 border border-accent/30 rounded-lg p-3 my-3 flex items-start gap-3">
      <Key size={16} className="text-accent mt-0.5 shrink-0" />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-mono font-bold text-white">Bring Your Own Key (BYOK)</p>
        <p className="text-xs font-mono text-muted mt-1">
          Paste your Nansen API key to unlock token deep dives with real smart money data.
          Stored locally in your browser — never sent to our server. Get a key at{" "}
          <a href="https://app.nansen.ai/auth/agent-setup" target="_blank" rel="noopener noreferrer" className="text-accent hover:underline">
            app.nansen.ai
          </a>
        </p>
      </div>
      <button
        onClick={() => setDismissed(true)}
        className="text-muted hover:text-white text-xs font-mono shrink-0"
        aria-label="Dismiss"
      >
        &times;
      </button>
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

  const [watchlist, setWatchlist] = useState<string[]>(getWatchlist);
  useEffect(() => {
    const handler = () => setWatchlist(getWatchlist());
    window.addEventListener("watchlist-change", handler);
    return () => window.removeEventListener("watchlist-change", handler);
  }, []);

  const watchedTokens = filteredResults.filter(
    (r) => watchlist.includes(r.token_address.toLowerCase())
  );

  return (
    <main className="max-w-7xl mx-auto px-4 py-4">
      <Header timestamp={data?.timestamp} isDemo={data?.demo} />

      <ByokBanner />

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

          <div className="py-4">
            <CLIActivity />
          </div>

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
