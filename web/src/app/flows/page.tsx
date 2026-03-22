"use client";

import useSWR from "swr";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Cell,
} from "recharts";
import { FlowsData, ChainFlow, SectorFlow } from "@/lib/types";
import { fetcher } from "@/lib/api";
import { fmtUsd, chainLabel, cn } from "@/lib/utils";
import { Card, CardHeader, CardValue } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { CardSkeleton, ChartSkeleton } from "@/components/ui/Skeleton";

const BULLISH = "#4ade80";
const BEARISH = "#f43f5e";

interface MomentumRow {
  chain: string;
  label: string;
  momentum_score: number;
  fill: string;
}

function buildMomentumRows(
  chains: Record<string, ChainFlow>,
): MomentumRow[] {
  return Object.entries(chains)
    .map(([chain, flow]) => ({
      chain,
      label: chainLabel(chain),
      momentum_score: flow.momentum_score,
      fill: flow.momentum_score >= 0 ? BULLISH : BEARISH,
    }))
    .sort((a, b) => b.momentum_score - a.momentum_score);
}

interface SectorRow {
  name: string;
  token_count: number;
  net_flow: number;
  tokens: string[];
  absFlow: number;
}

function buildSectorRows(
  sectors: Record<string, SectorFlow>,
): SectorRow[] {
  return Object.entries(sectors)
    .map(([name, s]) => ({
      name,
      token_count: s.token_count,
      net_flow: s.net_flow,
      tokens: s.tokens,
      absFlow: Math.abs(s.net_flow),
    }))
    .sort((a, b) => b.absFlow - a.absFlow);
}

function MomentumTooltip({ active, payload }: { active?: boolean; payload?: { payload: MomentumRow }[] }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="bg-surface border border-border rounded px-3 py-2 text-xs font-mono">
      <div className="text-white font-bold">{d.label}</div>
      <div className={d.momentum_score >= 0 ? "text-bullish" : "text-bearish"}>
        Momentum: {d.momentum_score.toFixed(1)}
      </div>
    </div>
  );
}

export default function FlowsPage() {
  const { data, error, isLoading } = useSWR<FlowsData>(
    "/api/flows",
    fetcher,
    { refreshInterval: 60000 },
  );

  return (
    <main className="max-w-7xl mx-auto px-4 py-4">
      <div className="flex items-center gap-3 mb-6">
        <h1 className="text-2xl font-mono font-bold text-accent">
          Cross-Chain Flows
        </h1>
        {data?.timestamp && (
          <span className="text-xs font-mono text-muted">
            {new Date(data.timestamp).toLocaleString()}
          </span>
        )}
      </div>

      {isLoading && (
        <div className="space-y-6">
          <ChartSkeleton height="h-72" />
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
            {Array.from({ length: 8 }).map((_, i) => (
              <CardSkeleton key={i} />
            ))}
          </div>
        </div>
      )}

      {error && (
        <div className="bg-surface border border-bearish rounded-lg p-4 font-mono text-sm text-bearish">
          Failed to load flows data. The API may still be running its first scan.
        </div>
      )}

      {data && (
        <>
          {/* ── Chain Momentum Chart ── */}
          <section className="mb-8">
            <h2 className="font-mono font-bold text-sm text-muted mb-3">
              CHAIN MOMENTUM
            </h2>
            <div className="bg-surface border border-border rounded-lg p-4">
              <ResponsiveContainer width="100%" height={Math.max(200, Object.keys(data.chains).length * 44)}>
                <BarChart
                  layout="vertical"
                  data={buildMomentumRows(data.chains)}
                  margin={{ top: 4, right: 20, bottom: 4, left: 4 }}
                >
                  <XAxis
                    type="number"
                    tick={{ fill: "#737373", fontSize: 11, fontFamily: "monospace" }}
                    axisLine={{ stroke: "#2a2a2a" }}
                    tickLine={false}
                  />
                  <YAxis
                    type="category"
                    dataKey="label"
                    width={50}
                    tick={{ fill: "#d4d4d4", fontSize: 12, fontFamily: "monospace", fontWeight: 600 }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <Tooltip
                    content={<MomentumTooltip />}
                    cursor={{ fill: "rgba(255,255,255,0.04)" }}
                  />
                  <Bar dataKey="momentum_score" radius={[0, 4, 4, 0]} barSize={24}>
                    {buildMomentumRows(data.chains).map((row) => (
                      <Cell key={row.chain} fill={row.fill} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </section>

          {/* ── Chain Cards Grid ── */}
          <section className="mb-8">
            <h2 className="font-mono font-bold text-sm text-muted mb-3">
              CHAIN BREAKDOWN
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
              {Object.entries(data.chains)
                .sort(([, a], [, b]) => b.momentum_score - a.momentum_score)
                .map(([chain, flow]) => (
                  <Card
                    key={chain}
                    glow={flow.momentum_score > 0 ? "green" : flow.momentum_score < 0 ? "red" : null}
                  >
                    <div className="flex items-center justify-between mb-3">
                      <CardHeader className="mb-0">
                        {chainLabel(chain)}
                      </CardHeader>
                      <Badge
                        variant="confidence"
                        value={flow.momentum_score >= 0 ? "HIGH" : "LOW"}
                        className="text-[10px]"
                      >
                        {flow.momentum_score >= 0 ? "BULLISH" : "BEARISH"}
                      </Badge>
                    </div>

                    <CardValue className={flow.sm_flow_total >= 0 ? "text-bullish" : "text-bearish"}>
                      {fmtUsd(flow.sm_flow_total)}
                    </CardValue>
                    <div className="text-xs font-mono text-muted mt-0.5">
                      SM Net Flow
                    </div>

                    <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 mt-3 text-xs font-mono">
                      <div className="flex justify-between">
                        <span className="text-muted">Tokens</span>
                        <span className="text-white">{flow.token_count}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted">Traders</span>
                        <span className="text-white">{flow.trader_count}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted">ACC</span>
                        <span className="text-bullish">{flow.accumulation}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted">DIS</span>
                        <span className="text-bearish">{flow.distribution}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted">Buy Vol</span>
                        <span className="text-bullish">{fmtUsd(flow.sm_buy_total)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted">Sell Vol</span>
                        <span className="text-bearish">{fmtUsd(flow.sm_sell_total)}</span>
                      </div>
                      <div className="flex justify-between col-span-2">
                        <span className="text-muted">HIGH Confidence</span>
                        <span className="text-accent font-bold">{flow.high_confidence}</span>
                      </div>
                    </div>
                  </Card>
                ))}
            </div>
          </section>

          {/* ── Sector Rotation ── */}
          <section className="mb-8">
            <h2 className="font-mono font-bold text-sm text-muted mb-3">
              SECTOR ROTATION
            </h2>
            <div className="bg-surface border border-border rounded-lg overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-sm font-mono">
                  <thead>
                    <tr className="border-b border-border text-muted text-xs">
                      <th className="text-left p-3">Sector</th>
                      <th className="text-right p-3">Tokens</th>
                      <th className="text-right p-3">Net Flow</th>
                      <th className="text-left p-3">Top Tokens</th>
                    </tr>
                  </thead>
                  <tbody>
                    {buildSectorRows(data.sectors).map((row) => (
                      <tr
                        key={row.name}
                        className="border-b border-border/50 hover:bg-surface-hover transition-colors"
                      >
                        <td className="p-3 text-white font-bold whitespace-nowrap">
                          {row.name}
                        </td>
                        <td className="p-3 text-right text-muted">
                          {row.token_count}
                        </td>
                        <td
                          className={cn(
                            "p-3 text-right font-bold",
                            row.net_flow > 0 ? "text-bullish" : row.net_flow < 0 ? "text-bearish" : "text-muted",
                          )}
                        >
                          {fmtUsd(row.net_flow)}
                        </td>
                        <td className="p-3">
                          <div className="flex flex-wrap gap-1">
                            {row.tokens.slice(0, 6).map((t) => (
                              <Badge key={t} className="text-[10px]">
                                {t}
                              </Badge>
                            ))}
                            {row.tokens.length > 6 && (
                              <span className="text-muted text-xs">
                                +{row.tokens.length - 6}
                              </span>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                    {buildSectorRows(data.sectors).length === 0 && (
                      <tr>
                        <td colSpan={4} className="p-6 text-center text-muted">
                          No sector data available yet.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </section>
        </>
      )}

      {!isLoading && !error && !data && (
        <div className="text-center py-20">
          <h2 className="text-2xl font-mono font-bold text-accent mb-4">
            CROSS-CHAIN FLOWS
          </h2>
          <p className="text-muted">Waiting for first scan to complete...</p>
          <p className="text-muted text-sm mt-2">
            The scanner runs automatically every 30 minutes.
          </p>
        </div>
      )}
    </main>
  );
}
