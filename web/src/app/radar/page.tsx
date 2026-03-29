"use client";

import useSWR from "swr";
import { useMemo } from "react";
import Link from "next/link";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Cell,
} from "recharts";
import { ScanData, RadarToken } from "@/lib/types";
import { fetcher } from "@/lib/api";
import { fmtUsd, chainLabel, cn, DEXSCREENER_SLUGS } from "@/lib/utils";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { ChartSkeleton, TableSkeleton } from "@/components/ui/Skeleton";

interface ChartDatum {
  symbol: string;
  flow: number;
  absFlow: number;
}

function FlowTooltip({ active, payload }: { active?: boolean; payload?: { value: number; payload: ChartDatum }[] }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="bg-surface border border-border rounded px-3 py-2 text-xs font-mono">
      <p className="text-white font-bold">{d.symbol}</p>
      <p className={d.flow >= 0 ? "text-bullish" : "text-bearish"}>
        {fmtUsd(d.flow)} net flow
      </p>
    </div>
  );
}

export default function RadarPage() {
  const { data, error, isLoading } = useSWR<ScanData>(
    "/api/scan/latest",
    fetcher,
    { refreshInterval: 60000 },
  );

  const radar = useMemo(() => data?.radar ?? [], [data]);

  const chartData = useMemo<ChartDatum[]>(() => {
    if (!radar.length) return [];
    return [...radar]
      .sort((a, b) => Math.abs(b.sm_net_flow_24h) - Math.abs(a.sm_net_flow_24h))
      .slice(0, 10)
      .map((t) => ({
        symbol: t.token_symbol,
        flow: t.sm_net_flow_24h,
        absFlow: Math.abs(t.sm_net_flow_24h),
      }));
  }, [radar]);

  const sorted = useMemo<RadarToken[]>(() => {
    return [...radar].sort(
      (a, b) => Math.abs(b.sm_net_flow_24h) - Math.abs(a.sm_net_flow_24h),
    );
  }, [radar]);

  /* ---- Loading ---- */
  if (isLoading) {
    return (
      <main className="max-w-7xl mx-auto px-4 py-4">
        <div className="flex items-center gap-3 mb-6">
          <span className="w-2.5 h-2.5 rounded-full bg-bullish animate-live" />
          <h1 className="text-2xl font-mono font-bold text-white">
            PRE-BREAKOUT DETECTION
          </h1>
        </div>
        <ChartSkeleton height="h-72" />
        <div className="mt-6">
          <TableSkeleton rows={8} />
        </div>
      </main>
    );
  }

  /* ---- Error ---- */
  if (error) {
    return (
      <main className="max-w-7xl mx-auto px-4 py-4">
        <div className="bg-surface border border-bearish rounded-lg p-4 my-4 font-mono text-sm text-bearish">
          Failed to load radar data. The API may still be running its first scan.
        </div>
      </main>
    );
  }

  /* ---- Empty ---- */
  if (!radar.length) {
    return (
      <main className="max-w-7xl mx-auto px-4 py-4">
        <div className="flex items-center gap-3 mb-6">
          <span className="w-2.5 h-2.5 rounded-full bg-bullish animate-live" />
          <h1 className="text-2xl font-mono font-bold text-white">
            PRE-BREAKOUT DETECTION
          </h1>
        </div>
        <Card className="text-center py-16">
          <p className="text-muted font-mono">No radar tokens detected yet.</p>
          <p className="text-muted font-mono text-sm mt-2">
            The scanner surfaces SM-only tokens not yet in mainstream screeners.
          </p>
        </Card>
      </main>
    );
  }

  /* ---- Main render ---- */
  return (
    <main className="max-w-7xl mx-auto px-4 py-4">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <span className="w-2.5 h-2.5 rounded-full bg-bullish animate-live" />
        <h1 className="text-2xl font-mono font-bold text-white">
          PRE-BREAKOUT DETECTION
        </h1>
        <span className="text-xs font-mono text-muted ml-auto">
          {radar.length} token{radar.length !== 1 && "s"} on radar
        </span>
      </div>

      {/* Bar chart — top 10 by |flow| */}
      <Card className="mb-6">
        <h2 className="text-xs font-mono text-muted uppercase tracking-wider mb-3">
          TOP 10 SM NET FLOW (24H)
        </h2>
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={chartData} margin={{ top: 4, right: 8, bottom: 4, left: 0 }}>
            <XAxis
              dataKey="symbol"
              tick={{ fill: "#737373", fontSize: 11, fontFamily: "monospace" }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              tickFormatter={(v: number) => fmtUsd(v).replace("+", "")}
              tick={{ fill: "#737373", fontSize: 11, fontFamily: "monospace" }}
              axisLine={false}
              tickLine={false}
              width={60}
            />
            <Tooltip
              content={<FlowTooltip />}
              cursor={{ fill: "rgba(255,255,255,0.03)" }}
            />
            <Bar dataKey="flow" radius={[4, 4, 0, 0]}>
              {chartData.map((d, i) => (
                <Cell
                  key={i}
                  fill={d.flow >= 0 ? "#4ade80" : "#f43f5e"}
                  fillOpacity={0.85}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </Card>

      {/* Mobile: card layout */}
      <div className="md:hidden space-y-2">
        {sorted.map((t, i) => {
          const positive = t.sm_net_flow_24h >= 0;
          const slug = DEXSCREENER_SLUGS[t.chain] || t.chain;
          const dexUrl = `https://dexscreener.com/${slug}/${t.token_address}`;
          return (
            <Card
              key={`${t.chain}-${t.token_address}-${i}`}
              className={cn("border-l-4 !p-3", positive ? "border-l-bullish" : "border-l-bearish")}
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <Link href={`/token/${t.chain}/${t.token_address}`} className="text-white font-bold font-mono hover:text-accent transition-colors">
                    {t.token_symbol}
                  </Link>
                  <span className="text-muted text-xs font-mono">{chainLabel(t.chain)}</span>
                </div>
                <a href={dexUrl} target="_blank" rel="noopener noreferrer" className="text-accent hover:text-secondary text-xs font-mono" aria-label={`View ${t.token_symbol} on DexScreener`}>
                  Chart
                </a>
              </div>
              <div className="grid grid-cols-3 gap-2 text-xs font-mono mb-2">
                <div>
                  <div className="text-muted">Flow 24h</div>
                  <div className={cn("font-bold", positive ? "text-bullish" : "text-bearish")}>{fmtUsd(t.sm_net_flow_24h)}</div>
                </div>
                <div>
                  <div className="text-muted">Flow 7d</div>
                  <div className={t.sm_net_flow_7d >= 0 ? "text-bullish" : "text-bearish"}>{fmtUsd(t.sm_net_flow_7d)}</div>
                </div>
                <div>
                  <div className="text-muted">Traders</div>
                  <div className="text-white">{t.sm_trader_count}</div>
                </div>
              </div>
              <div className="flex items-center justify-between text-xs font-mono">
                <div className="flex flex-wrap gap-1">
                  {t.sm_sectors.map((s) => (
                    <Badge key={s} className="text-[10px] px-1.5 py-0">{s}</Badge>
                  ))}
                </div>
                <span className="text-muted">{t.market_cap > 0 ? fmtUsd(t.market_cap) : "--"}</span>
              </div>
            </Card>
          );
        })}
      </div>

      {/* Desktop: table layout */}
      <Card className="hidden md:block overflow-x-auto">
        <table className="w-full text-sm font-mono">
          <thead>
            <tr className="text-muted text-xs border-b border-border">
              <th className="text-left py-2 px-3">Symbol</th>
              <th className="text-left py-2 px-3">Chain</th>
              <th className="text-right py-2 px-3">Flow 24h</th>
              <th className="text-right py-2 px-3">Flow 7d</th>
              <th className="text-right py-2 px-3">Traders</th>
              <th className="text-left py-2 px-3">Sectors</th>
              <th className="text-right py-2 px-3">Market Cap</th>
              <th className="text-center py-2 px-3">Chart</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((t, i) => {
              const positive = t.sm_net_flow_24h >= 0;
              const slug = DEXSCREENER_SLUGS[t.chain] || t.chain;
              const dexUrl = `https://dexscreener.com/${slug}/${t.token_address}`;

              return (
                <tr
                  key={`${t.chain}-${t.token_address}-${i}`}
                  className={cn(
                    "border-b border-border/50 hover:bg-surface-hover transition-colors",
                    positive
                      ? "border-l-2 border-l-bullish"
                      : "border-l-2 border-l-bearish",
                  )}
                >
                  <td className="py-2.5 px-3">
                    <Link href={`/token/${t.chain}/${t.token_address}`} className="text-white font-bold hover:text-accent transition-colors">
                      {t.token_symbol}
                    </Link>
                  </td>
                  <td className="py-2.5 px-3 text-muted">{chainLabel(t.chain)}</td>
                  <td className={cn("py-2.5 px-3 text-right font-bold", positive ? "text-bullish" : "text-bearish")}>
                    {fmtUsd(t.sm_net_flow_24h)}
                  </td>
                  <td className={cn("py-2.5 px-3 text-right", t.sm_net_flow_7d >= 0 ? "text-bullish" : "text-bearish")}>
                    {fmtUsd(t.sm_net_flow_7d)}
                  </td>
                  <td className="py-2.5 px-3 text-right text-white">{t.sm_trader_count}</td>
                  <td className="py-2.5 px-3">
                    <div className="flex flex-wrap gap-1">
                      {t.sm_sectors.map((s) => (
                        <Badge key={s} className="text-[10px] px-1.5 py-0">{s}</Badge>
                      ))}
                    </div>
                  </td>
                  <td className="py-2.5 px-3 text-right text-muted">{t.market_cap > 0 ? fmtUsd(t.market_cap) : "--"}</td>
                  <td className="py-2.5 px-3 text-center">
                    <a href={dexUrl} target="_blank" rel="noopener noreferrer" className="text-accent hover:text-secondary text-xs transition-colors" aria-label={`View ${t.token_symbol} on DexScreener`}>
                      View
                    </a>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </Card>
    </main>
  );
}
