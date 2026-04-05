"use client";

import useSWR from "swr";
import { useMemo } from "react";
import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Tooltip,
} from "recharts";
import { PerformanceStats, SignalLedger } from "@/lib/types";
import { fetcher } from "@/lib/api";
import { fmtPrice, chainLabel, cn } from "@/lib/utils";
import { Card, CardHeader, CardValue } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { CardSkeleton, TableSkeleton, ChartSkeleton } from "@/components/ui/Skeleton";

/* ------------------------------------------------------------------ */
/*  Chart colors                                                       */
/* ------------------------------------------------------------------ */

const PIE_COLORS = ["#4ade80", "#f43f5e"]; // wins, losses

const PHASE_COLORS: Record<string, string> = {
  ACCUMULATION: "#4ade80",
  DISTRIBUTION: "#f43f5e",
  MARKUP: "#6366f1",
  MARKDOWN: "#facc15",
};

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

/** Format a date string like "2026-04-01T12:00:00Z" → "Apr 01" */
function fmtDate(isoString: string): string {
  const d = new Date(isoString);
  return d.toLocaleDateString("en-US", { month: "short", day: "2-digit" });
}

/* ------------------------------------------------------------------ */
/*  Custom tooltip for donut chart                                     */
/* ------------------------------------------------------------------ */

function PieTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: { name: string; value: number }[];
}) {
  if (!active || !payload?.length) return null;
  const d = payload[0];
  return (
    <div className="bg-surface border border-border rounded px-3 py-2 text-xs font-mono">
      <p className="text-white font-bold">{d.name}</p>
      <p className="text-muted">{d.value} signals</p>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Center label for pie donut                                         */
/* ------------------------------------------------------------------ */

function PieCenterLabel({ winRate }: { winRate: number }) {
  return (
    <text
      x="50%"
      y="50%"
      textAnchor="middle"
      dominantBaseline="central"
      className="fill-white font-mono font-bold"
      style={{ fontSize: 22 }}
    >
      {(winRate * 100).toFixed(0)}%
    </text>
  );
}

/* ------------------------------------------------------------------ */
/*  Page                                                               */
/* ------------------------------------------------------------------ */

export default function PerformancePage() {
  const {
    data: perfData,
    error: perfError,
    isLoading: perfLoading,
  } = useSWR<PerformanceStats>("/api/v1/performance", fetcher, {
    refreshInterval: 60000,
  });

  const {
    data: ledgerData,
    error: ledgerError,
    isLoading: ledgerLoading,
  } = useSWR<SignalLedger>("/api/v1/signals?resolved_only=true&limit=100", fetcher, {
    refreshInterval: 60000,
  });

  const isLoading = perfLoading || ledgerLoading;
  const error = perfError ?? ledgerError;

  /* Pie data */
  const pieData = useMemo(() => {
    if (!perfData) return [];
    const wins = Math.round((perfData.resolved_signals ?? 0) * (perfData.win_rate ?? 0));
    const losses = (perfData.resolved_signals ?? 0) - wins;
    return [
      { name: "Wins", value: wins },
      { name: "Losses", value: losses },
    ];
  }, [perfData]);


  /* Phase breakdown rows sorted by signal count descending */
  const phaseRows = useMemo(() => {
    if (!perfData?.by_phase) return [];
    return Object.entries(perfData.by_phase).sort(
      ([, a], [, b]) => b.signal_count - a.signal_count,
    );
  }, [perfData]);

  /* Signal ledger rows */
  const signals = ledgerData?.signals ?? [];

  /* ---- Loading state ---- */
  if (isLoading) {
    return (
      <main className="max-w-7xl mx-auto px-4 py-4">
        <h1 className="text-2xl font-mono font-bold text-white mb-6">
          SIGNAL PERFORMANCE
        </h1>
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-2 sm:gap-3 mb-6">
          {Array.from({ length: 5 }).map((_, i) => (
            <CardSkeleton key={i} />
          ))}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
          <ChartSkeleton height="h-72" />
          <ChartSkeleton height="h-72" />
        </div>
        <TableSkeleton rows={8} />
      </main>
    );
  }

  /* ---- Error state ---- */
  if (error) {
    return (
      <main className="max-w-7xl mx-auto px-4 py-4">
        <h1 className="text-2xl font-mono font-bold text-white mb-6">
          SIGNAL PERFORMANCE
        </h1>
        <div className="bg-surface border border-bearish rounded-lg p-4 my-4 font-mono text-sm text-bearish">
          Failed to load performance data. The API may still be running its first scan.
        </div>
      </main>
    );
  }

  /* ---- Empty state ---- */
  if (!perfData || perfData.total_signals === 0) {
    return (
      <main className="max-w-7xl mx-auto px-4 py-4">
        <h1 className="text-2xl font-mono font-bold text-white mb-6">
          SIGNAL PERFORMANCE
        </h1>
        <Card className="text-center py-16">
          <p className="text-accent font-mono font-bold text-lg mb-3">Accumulating signal history...</p>
          <p className="text-muted font-mono text-sm max-w-md mx-auto leading-relaxed">
            The scanner saves each divergence signal and tracks price outcomes over time.
            Performance data appears after 2+ scan cycles with overlapping tokens.
          </p>
          <p className="text-muted/50 font-mono text-xs mt-4">
            Methodology: Volume/MCap ratio + price-volume divergence → Wyckoff phase → outcome tracking
          </p>
        </Card>
      </main>
    );
  }

  const winRatePct = (perfData.win_rate * 100).toFixed(1);
  const avgReturn = perfData.avg_return_on_wins;
  const profitFactor = perfData.profit_factor;

  /* ---- Main render ---- */
  return (
    <main className="max-w-7xl mx-auto px-4 py-4">
      <h1 className="text-2xl font-mono font-bold text-white mb-6">
        SIGNAL PERFORMANCE
      </h1>

      {/* ---- Stats row ---- */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-2 sm:gap-3 mb-6">
        <Card glow="green">
          <CardHeader>Win Rate</CardHeader>
          <CardValue className="text-bullish glow-green">
            {winRatePct}%
          </CardValue>
        </Card>

        <Card>
          <CardHeader>Total Signals</CardHeader>
          <CardValue className="text-accent">{perfData.total_signals}</CardValue>
        </Card>

        <Card>
          <CardHeader>Avg Return (wins)</CardHeader>
          <CardValue className={avgReturn != null && avgReturn >= 0 ? "text-bullish" : "text-bearish"}>
            {avgReturn != null
              ? `${avgReturn >= 0 ? "+" : ""}${avgReturn.toFixed(1)}%`
              : "—"}
          </CardValue>
        </Card>

        <Card>
          <CardHeader>Profit Factor</CardHeader>
          <CardValue className={profitFactor != null && profitFactor >= 1 ? "text-bullish" : "text-muted"}>
            {profitFactor != null ? profitFactor.toFixed(2) : "—"}
          </CardValue>
        </Card>

        <Card>
          <CardHeader>Pending</CardHeader>
          <CardValue className="text-muted">{perfData.pending_signals}</CardValue>
        </Card>
      </div>

      {/* ---- Charts row ---- */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
        {/* Win/Loss donut */}
        <Card>
          <h2 className="text-xs font-mono text-muted uppercase tracking-wider mb-3">
            WIN / LOSS RATIO
          </h2>
          <ResponsiveContainer width="100%" height={280}>
            <PieChart>
              <Pie
                data={pieData}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                innerRadius={70}
                outerRadius={110}
                strokeWidth={0}
              >
                {pieData.map((_, i) => (
                  <Cell key={i} fill={PIE_COLORS[i]} fillOpacity={0.85} />
                ))}
              </Pie>
              <Tooltip content={<PieTooltip />} />
              <PieCenterLabel winRate={perfData.win_rate} />
            </PieChart>
          </ResponsiveContainer>
          <div className="flex justify-center gap-6 text-xs font-mono mt-2">
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-bullish inline-block" />
              Wins ({pieData[0]?.value ?? 0})
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-bearish inline-block" />
              Losses ({pieData[1]?.value ?? 0})
            </span>
          </div>
        </Card>

        {/* Phase breakdown table */}
        <Card>
          <h2 className="text-xs font-mono text-muted uppercase tracking-wider mb-3">
            PERFORMANCE BY PHASE
          </h2>
          {phaseRows.length === 0 ? (
            <div className="flex items-center justify-center h-48 text-muted font-mono text-sm">
              No phase data yet
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm font-mono">
                <thead>
                  <tr className="text-muted text-xs border-b border-border">
                    <th className="text-left py-2 px-3">Phase</th>
                    <th className="text-right py-2 px-3">Signals</th>
                    <th className="text-right py-2 px-3">Win Rate</th>
                    <th className="text-right py-2 px-3">Avg Return</th>
                  </tr>
                </thead>
                <tbody>
                  {phaseRows.map(([phase, row]) => {
                    const phaseColor = PHASE_COLORS[phase] ?? "#737373";
                    const wr = (row.win_rate * 100).toFixed(0);
                    const ar = row.avg_return;
                    return (
                      <tr key={phase} className="border-b border-border/50 hover:bg-surface-hover transition-colors">
                        <td className="py-2.5 px-3">
                          <span className="flex items-center gap-2">
                            <span
                              className="w-2 h-2 rounded-full inline-block flex-shrink-0"
                              style={{ backgroundColor: phaseColor }}
                            />
                            <Badge variant="phase" value={phase}>{phase}</Badge>
                          </span>
                        </td>
                        <td className="py-2.5 px-3 text-right text-white">{row.signal_count}</td>
                        <td className={cn(
                          "py-2.5 px-3 text-right font-bold",
                          row.win_rate >= 0.5 ? "text-bullish" : "text-bearish",
                        )}>
                          {wr}%
                        </td>
                        <td className={cn(
                          "py-2.5 px-3 text-right",
                          ar == null ? "text-muted" : ar >= 0 ? "text-bullish" : "text-bearish",
                        )}>
                          {ar != null ? `${ar >= 0 ? "+" : ""}${ar.toFixed(1)}%` : "—"}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>

      {/* ---- Signal ledger ---- */}
      <Card>
        <h2 className="text-xs font-mono text-muted uppercase tracking-wider mb-3">
          SIGNAL LEDGER ({signals.length})
        </h2>

        {signals.length === 0 ? (
          <div className="text-center py-12 text-muted font-mono text-sm">
            No resolved signals yet. Check back after the next scan cycle.
          </div>
        ) : (
          <>
            {/* Mobile: card layout */}
            <div className="md:hidden space-y-2">
              {signals.map((s) => {
                const r72 = s.return_72h;
                const positive = r72 != null && r72 >= 0;
                const outcome = s.outcome_correct;
                return (
                  <div
                    key={s.id}
                    className={cn(
                      "bg-bg/50 border border-border/50 rounded-lg p-3 border-l-4",
                      outcome === 1
                        ? "border-l-bullish"
                        : outcome === 0
                        ? "border-l-bearish"
                        : "border-l-border",
                    )}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className="text-white font-bold font-mono">{s.token_symbol}</span>
                        <span className="text-muted text-xs font-mono">{chainLabel(s.chain)}</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <Badge variant="phase" value={s.phase}>{s.phase}</Badge>
                        <span className="text-xs font-mono text-muted">{fmtDate(s.created_at)}</span>
                      </div>
                    </div>
                    <div className="grid grid-cols-3 gap-2 text-xs font-mono">
                      <div>
                        <div className="text-muted">Entry</div>
                        <div className="text-white">
                          {s.price_at_emission != null ? fmtPrice(s.price_at_emission) : "—"}
                        </div>
                      </div>
                      <div>
                        <div className="text-muted">72h Return</div>
                        <div className={cn("font-bold", r72 == null ? "text-muted" : positive ? "text-bullish" : "text-bearish")}>
                          {r72 != null ? `${positive ? "+" : ""}${r72.toFixed(1)}%` : "—"}
                        </div>
                      </div>
                      <div>
                        <div className="text-muted">Outcome</div>
                        <div className={cn(
                          "font-bold text-base",
                          outcome === 1 ? "text-bullish" : outcome === 0 ? "text-bearish" : "text-muted",
                        )}>
                          {outcome === 1 ? "✓" : outcome === 0 ? "✗" : "—"}
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Desktop: table layout */}
            <div className="hidden md:block overflow-x-auto">
              <table className="w-full text-sm font-mono">
                <thead>
                  <tr className="text-muted text-xs border-b border-border">
                    <th className="text-left py-2 px-3">Date</th>
                    <th className="text-left py-2 px-3">Token</th>
                    <th className="text-left py-2 px-3">Chain</th>
                    <th className="text-left py-2 px-3">Phase</th>
                    <th className="text-right py-2 px-3">Strength</th>
                    <th className="text-right py-2 px-3">Entry Price</th>
                    <th className="text-right py-2 px-3">72h Return</th>
                    <th className="text-center py-2 px-3">Outcome</th>
                  </tr>
                </thead>
                <tbody>
                  {signals.map((s) => {
                    const r72 = s.return_72h;
                    const positive = r72 != null && r72 >= 0;
                    const outcome = s.outcome_correct;

                    return (
                      <tr
                        key={s.id}
                        className="border-b border-border/50 hover:bg-surface-hover transition-colors"
                      >
                        <td className="py-2.5 px-3 text-muted">{fmtDate(s.created_at)}</td>
                        <td className="py-2.5 px-3 text-white font-bold">{s.token_symbol}</td>
                        <td className="py-2.5 px-3 text-muted">{chainLabel(s.chain)}</td>
                        <td className="py-2.5 px-3">
                          <Badge variant="phase" value={s.phase}>{s.phase}</Badge>
                        </td>
                        <td className="py-2.5 px-3 text-right text-white">{s.divergence_strength}</td>
                        <td className="py-2.5 px-3 text-right text-muted">
                          {s.price_at_emission != null ? fmtPrice(s.price_at_emission) : "—"}
                        </td>
                        <td className={cn(
                          "py-2.5 px-3 text-right font-bold",
                          r72 == null ? "text-muted" : positive ? "text-bullish" : "text-bearish",
                        )}>
                          {r72 != null ? `${positive ? "+" : ""}${r72.toFixed(1)}%` : "—"}
                        </td>
                        <td className={cn(
                          "py-2.5 px-3 text-center font-bold text-base",
                          outcome === 1 ? "text-bullish" : outcome === 0 ? "text-bearish" : "text-muted",
                        )}>
                          {outcome === 1 ? "✓" : outcome === 0 ? "✗" : "—"}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </>
        )}
      </Card>
    </main>
  );
}
