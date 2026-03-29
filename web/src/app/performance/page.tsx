"use client";

import useSWR from "swr";
import { useMemo } from "react";
import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";
import { OutcomesData, ScanData, SignalOutcome } from "@/lib/types";
import { fetcher } from "@/lib/api";
import { fmtPrice, fmtPct, chainLabel, cn } from "@/lib/utils";
import { Card, CardHeader, CardValue } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { CardSkeleton, ChartSkeleton, TableSkeleton } from "@/components/ui/Skeleton";

/* ------------------------------------------------------------------ */
/*  Chart colors                                                      */
/* ------------------------------------------------------------------ */

const PIE_COLORS = ["#4ade80", "#f43f5e"]; // wins, losses

const PHASE_COLORS: Record<string, string> = {
  ACCUMULATION: "#4ade80",
  DISTRIBUTION: "#f43f5e",
  MARKUP: "#6366f1",
  MARKDOWN: "#facc15",
};

/* ------------------------------------------------------------------ */
/*  Custom tooltips                                                   */
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

function ScatterTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: { payload: SignalOutcome }[];
}) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="bg-surface border border-border rounded px-3 py-2 text-xs font-mono">
      <p className="text-white font-bold">{d.token_symbol}</p>
      <p className="text-muted">{d.chain} &middot; {d.phase}</p>
      <p className={d.price_change_pct >= 0 ? "text-bullish" : "text-bearish"}>
        {d.price_change_pct >= 0 ? "+" : ""}
        {d.price_change_pct.toFixed(1)}% &middot; {d.days_ago}d ago
      </p>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Center label for pie donut                                        */
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
      {winRate.toFixed(0)}%
    </text>
  );
}

/* ------------------------------------------------------------------ */
/*  Page                                                              */
/* ------------------------------------------------------------------ */

export default function PerformancePage() {
  const {
    data: outcomes,
    error: outcomesError,
    isLoading: outcomesLoading,
  } = useSWR<OutcomesData>("/api/history/outcomes?days=30", fetcher, {
    refreshInterval: 60000,
  });

  const {
    data: scan,
    error: scanError,
    isLoading: scanLoading,
  } = useSWR<ScanData>("/api/scan/latest", fetcher, {
    refreshInterval: 60000,
  });

  const isLoading = outcomesLoading || scanLoading;
  const error = outcomesError || scanError;

  /* Derive stats — prefer outcomes endpoint, fall back to scan backtest */
  const stats = outcomes?.stats ?? scan?.backtest ?? null;
  const outcomeList = outcomes?.outcomes ?? [];

  /* Pie data */
  const pieData = useMemo(() => {
    if (!stats) return [];
    return [
      { name: "Wins", value: stats.wins },
      { name: "Losses", value: stats.losses },
    ];
  }, [stats]);

  /* Scatter data grouped by phase for coloring */
  const scatterByPhase = useMemo(() => {
    const groups: Record<string, SignalOutcome[]> = {};
    for (const o of outcomeList) {
      const phase = o.phase || "UNKNOWN";
      if (!groups[phase]) groups[phase] = [];
      groups[phase].push(o);
    }
    return groups;
  }, [outcomeList]);

  /* Sorted outcomes for table */
  const sortedOutcomes = useMemo(() => {
    return [...outcomeList].sort((a, b) => a.days_ago - b.days_ago);
  }, [outcomeList]);

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
  if (!stats || stats.total_signals === 0) {
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

  /* ---- Main render ---- */
  return (
    <main className="max-w-7xl mx-auto px-4 py-4">
      <h1 className="text-2xl font-mono font-bold text-white mb-6">
        SIGNAL PERFORMANCE
      </h1>

      {scan?.demo && (
        <div className="bg-accent/10 border border-accent/30 text-accent font-mono text-xs px-3 py-1.5 rounded mb-4 text-center">
          DEMO DATA — backtest stats are seeded. Live results appear after 2+ scan cycles.
        </div>
      )}

      {/* ---- Stats row ---- */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-2 sm:gap-3 mb-6">
        <Card glow="green">
          <CardHeader>Win Rate</CardHeader>
          <CardValue className="text-bullish glow-green">
            {stats.win_rate.toFixed(1)}%
          </CardValue>
        </Card>

        <Card>
          <CardHeader>Total Signals</CardHeader>
          <CardValue className="text-accent">{stats.total_signals}</CardValue>
        </Card>

        <Card>
          <CardHeader>Avg Return</CardHeader>
          <CardValue
            className={stats.avg_return >= 0 ? "text-bullish" : "text-bearish"}
          >
            {stats.avg_return >= 0 ? "+" : ""}{stats.avg_return.toFixed(1)}%
          </CardValue>
        </Card>

        <Card>
          <CardHeader>Best Return</CardHeader>
          <CardValue className="text-bullish">+{stats.best_return.toFixed(1)}%</CardValue>
        </Card>

        <Card>
          <CardHeader>Worst Return</CardHeader>
          <CardValue className="text-bearish">{stats.worst_return.toFixed(1)}%</CardValue>
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
              <PieCenterLabel winRate={stats.win_rate} />
            </PieChart>
          </ResponsiveContainer>
          <div className="flex justify-center gap-6 text-xs font-mono mt-2">
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-bullish inline-block" />
              Wins ({stats.wins})
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-bearish inline-block" />
              Losses ({stats.losses})
            </span>
          </div>
        </Card>

        {/* Scatter timeline */}
        <Card>
          <h2 className="text-xs font-mono text-muted uppercase tracking-wider mb-3">
            SIGNAL TIMELINE (30D)
          </h2>
          <ResponsiveContainer width="100%" height={280}>
            <ScatterChart margin={{ top: 8, right: 8, bottom: 8, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2a2a2a" />
              <XAxis
                dataKey="days_ago"
                name="Days Ago"
                type="number"
                reversed
                tick={{ fill: "#737373", fontSize: 11, fontFamily: "monospace" }}
                axisLine={false}
                tickLine={false}
                label={{
                  value: "Days Ago",
                  position: "insideBottom",
                  offset: -2,
                  fill: "#737373",
                  fontSize: 10,
                  fontFamily: "monospace",
                }}
              />
              <YAxis
                dataKey="price_change_pct"
                name="Return"
                type="number"
                tickFormatter={(v: number) => `${v.toFixed(0)}%`}
                tick={{ fill: "#737373", fontSize: 11, fontFamily: "monospace" }}
                axisLine={false}
                tickLine={false}
                width={50}
              />
              <Tooltip content={<ScatterTooltip />} />
              {Object.entries(scatterByPhase).map(([phase, data]) => (
                <Scatter
                  key={phase}
                  name={phase}
                  data={data}
                  fill={PHASE_COLORS[phase] || "#737373"}
                  fillOpacity={0.8}
                />
              ))}
            </ScatterChart>
          </ResponsiveContainer>
          <div className="flex justify-center gap-4 text-xs font-mono mt-2 flex-wrap">
            {Object.entries(PHASE_COLORS).map(([phase, color]) => (
              <span key={phase} className="flex items-center gap-1.5">
                <span
                  className="w-2.5 h-2.5 rounded-full inline-block"
                  style={{ backgroundColor: color }}
                />
                {phase}
              </span>
            ))}
          </div>
        </Card>
      </div>

      {/* ---- Outcomes ---- */}
      <Card>
        <h2 className="text-xs font-mono text-muted uppercase tracking-wider mb-3">
          SIGNAL OUTCOMES ({sortedOutcomes.length})
        </h2>

        {/* Mobile: card layout */}
        <div className="md:hidden space-y-2">
          {sortedOutcomes.map((o, i) => {
            const returnPct = o.price_change_pct * 100;
            const positive = o.price_change_pct >= 0;
            return (
              <div
                key={`${o.chain}-${o.token_symbol}-${i}`}
                className={cn(
                  "bg-bg/50 border border-border/50 rounded-lg p-3 border-l-4",
                  positive ? "border-l-bullish" : "border-l-bearish",
                )}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="text-white font-bold font-mono">{o.token_symbol}</span>
                    <span className="text-muted text-xs font-mono">{chainLabel(o.chain)}</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <Badge variant="phase" value={o.phase}>{o.phase}</Badge>
                    <Badge variant="confidence" value={o.confidence}>{o.confidence}</Badge>
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-2 text-xs font-mono">
                  <div>
                    <div className="text-muted">Signal</div>
                    <div className="text-white">{fmtPrice(o.signal_price)}</div>
                  </div>
                  <div>
                    <div className="text-muted">Current</div>
                    <div className="text-white">{fmtPrice(o.current_price)}</div>
                  </div>
                  <div>
                    <div className="text-muted">Return</div>
                    <div className={cn("font-bold", positive ? "text-bullish" : "text-bearish")}>
                      {positive ? "+" : ""}{returnPct.toFixed(1)}%
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
                <th className="text-left py-2 px-3">Symbol</th>
                <th className="text-left py-2 px-3">Chain</th>
                <th className="text-left py-2 px-3">Phase</th>
                <th className="text-center py-2 px-3">Confidence</th>
                <th className="text-right py-2 px-3">Signal Price</th>
                <th className="text-right py-2 px-3">Current Price</th>
                <th className="text-right py-2 px-3">Return %</th>
                <th className="text-right py-2 px-3">Days Ago</th>
              </tr>
            </thead>
            <tbody>
              {sortedOutcomes.map((o, i) => {
                const returnPct = o.price_change_pct * 100;
                const positive = o.price_change_pct >= 0;

                return (
                  <tr
                    key={`${o.chain}-${o.token_symbol}-${i}`}
                    className={cn(
                      "border-b border-border/50 hover:bg-surface-hover transition-colors",
                      positive
                        ? "border-l-2 border-l-bullish"
                        : "border-l-2 border-l-bearish",
                    )}
                  >
                    <td className="py-2.5 px-3 text-white font-bold">{o.token_symbol}</td>
                    <td className="py-2.5 px-3 text-muted">{chainLabel(o.chain)}</td>
                    <td className="py-2.5 px-3">
                      <Badge variant="phase" value={o.phase}>{o.phase}</Badge>
                    </td>
                    <td className="py-2.5 px-3 text-center">
                      <Badge variant="confidence" value={o.confidence}>{o.confidence}</Badge>
                    </td>
                    <td className="py-2.5 px-3 text-right text-muted">{fmtPrice(o.signal_price)}</td>
                    <td className="py-2.5 px-3 text-right text-white">{fmtPrice(o.current_price)}</td>
                    <td className={cn("py-2.5 px-3 text-right font-bold", positive ? "text-bullish" : "text-bearish")}>
                      {positive ? "+" : ""}{returnPct.toFixed(1)}%
                    </td>
                    <td className="py-2.5 px-3 text-right text-muted">{o.days_ago}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>
    </main>
  );
}
