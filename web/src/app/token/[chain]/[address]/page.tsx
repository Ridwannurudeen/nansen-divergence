"use client";

import { use } from "react";
import useSWR from "swr";
import Link from "next/link";
import {
  BarChart,
  Bar,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts";
import { ArrowLeft, ExternalLink } from "lucide-react";
import { Token, DeepDiveData } from "@/lib/types";
import { fetcher } from "@/lib/api";
import { fmtUsd, fmtPct, fmtPrice, chainLabel, cn, DEXSCREENER_SLUGS } from "@/lib/utils";
import { Card, CardHeader } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Skeleton, CardSkeleton, ChartSkeleton } from "@/components/ui/Skeleton";

/* ---------- helpers ---------- */

const EXPLORER_URLS: Record<string, string> = {
  ethereum: "https://etherscan.io/token/",
  bnb: "https://bscscan.com/token/",
  solana: "https://solscan.io/token/",
  base: "https://basescan.org/token/",
  arbitrum: "https://arbiscan.io/token/",
  polygon: "https://polygonscan.com/token/",
  optimism: "https://optimistic.etherscan.io/token/",
  avalanche: "https://snowtrace.io/token/",
  linea: "https://lineascan.build/token/",
};

const EXPLORER_LABELS: Record<string, string> = {
  ethereum: "Etherscan",
  bnb: "BscScan",
  solana: "Solscan",
  base: "BaseScan",
  arbitrum: "Arbiscan",
  polygon: "PolygonScan",
  optimism: "OP Etherscan",
  avalanche: "Snowtrace",
  linea: "LineaScan",
};

const FLOW_COLORS: Record<string, string> = {
  whale: "#6366f1",
  smart_trader: "#f97316",
  exchange: "#facc15",
  fresh_wallet: "#4ade80",
};

function truncAddr(addr: string): string {
  if (addr.length <= 12) return addr;
  return `${addr.slice(0, 6)}...${addr.slice(-4)}`;
}

function AlphaBar({ score }: { score: number }) {
  const color = score >= 70 ? "#f43f5e" : score >= 40 ? "#f97316" : "#6366f1";
  return (
    <div className="flex items-center gap-3 w-full max-w-xs">
      <div className="flex-1 h-2 bg-border rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${score}%`, backgroundColor: color }}
        />
      </div>
      <span className="text-sm font-mono font-bold" style={{ color }}>
        {score}
      </span>
    </div>
  );
}

/* ---------- sub-components ---------- */

function SummarySection({ token }: { token: Token }) {
  const flowColor = token.sm_net_flow > 0 ? "text-bullish" : "text-bearish";
  const priceColor = token.price_change > 0 ? "text-bullish" : "text-bearish";

  return (
    <div className="space-y-4 animate-fade-in">
      {/* Title row */}
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-mono font-bold text-white">
          {token.token_symbol}
        </h1>
        <Badge variant="phase" value={token.phase}>
          {token.phase}
        </Badge>
        <Badge variant="confidence" value={token.confidence}>
          {token.confidence}
        </Badge>
        <span className="text-xs font-mono text-muted">
          {chainLabel(token.chain)}
        </span>
        {token.is_new && (
          <span className="text-xs bg-bearish text-white px-1.5 py-0.5 rounded font-mono font-bold">
            NEW
          </span>
        )}
      </div>

      {/* Narrative */}
      {token.narrative && (
        <p className="text-sm text-muted italic font-mono border-l-2 border-accent pl-3">
          {token.narrative}
        </p>
      )}

      {/* Metric grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Card>
          <CardHeader>Price</CardHeader>
          <div className={cn("text-xl font-mono font-bold", priceColor)}>
            {fmtPrice(token.price_usd)}
          </div>
          <div className={cn("text-xs font-mono mt-0.5", priceColor)}>
            {fmtPct(token.price_change)}
          </div>
        </Card>

        <Card>
          <CardHeader>Market Cap</CardHeader>
          <div className="text-xl font-mono font-bold text-white">
            {fmtUsd(token.market_cap)}
          </div>
        </Card>

        <Card glow={token.sm_net_flow > 0 ? "green" : "red"}>
          <CardHeader>SM Net Flow</CardHeader>
          <div className={cn("text-xl font-mono font-bold", flowColor)}>
            {fmtUsd(token.sm_net_flow)}
          </div>
          <div className="text-xs text-muted mt-0.5">
            {token.sm_trader_count} trader{token.sm_trader_count !== 1 ? "s" : ""}
          </div>
        </Card>

        <Card>
          <CardHeader>24h Volume</CardHeader>
          <div className="text-xl font-mono font-bold text-white">
            {fmtUsd(token.volume_24h)}
          </div>
        </Card>
      </div>

      {/* Alpha bar */}
      <Card>
        <CardHeader>Alpha Score</CardHeader>
        <div className="mt-2">
          <AlphaBar score={token.alpha_score} />
        </div>
      </Card>
    </div>
  );
}

function SMDonut({ token }: { token: Token }) {
  const buy = token.sm_buy_volume || 0;
  const sell = token.sm_sell_volume || 0;
  if (buy === 0 && sell === 0) {
    return (
      <Card>
        <CardHeader>SM Buy / Sell</CardHeader>
        <div className="text-sm text-muted py-8 text-center">No SM volume data.</div>
      </Card>
    );
  }

  const data = [
    { name: "Buy", value: buy },
    { name: "Sell", value: sell },
  ];
  const COLORS = ["#4ade80", "#f43f5e"];

  return (
    <Card>
      <CardHeader>SM Buy / Sell Volume</CardHeader>
      <ResponsiveContainer width="100%" height={220}>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={50}
            outerRadius={80}
            paddingAngle={3}
            dataKey="value"
            stroke="none"
          >
            {data.map((_, i) => (
              <Cell key={i} fill={COLORS[i]} />
            ))}
          </Pie>
          <Tooltip
            formatter={(v) => fmtUsd(Number(v))}
            contentStyle={{
              background: "#1a1a1a",
              border: "1px solid #2a2a2a",
              borderRadius: 6,
              fontFamily: "monospace",
              fontSize: 12,
            }}
          />
          <Legend
            formatter={(value: string) => (
              <span className="text-xs font-mono text-muted">{value}</span>
            )}
          />
        </PieChart>
      </ResponsiveContainer>
      <div className="flex justify-between text-xs font-mono px-2 -mt-2">
        <span className="text-bullish">Buy: {fmtUsd(buy)}</span>
        <span className="text-bearish">Sell: {fmtUsd(sell)}</span>
      </div>
    </Card>
  );
}

function FlowIntelligence({ flowData }: { flowData: Record<string, unknown> }) {
  // Parse flow_intelligence — expect label keys with buy/sell amounts
  const entries: { label: string; buy: number; sell: number }[] = [];

  for (const [key, val] of Object.entries(flowData)) {
    if (val && typeof val === "object") {
      const obj = val as Record<string, unknown>;
      const buy = Number(obj.buy || obj.buy_volume || obj.inflow || 0);
      const sell = Number(obj.sell || obj.sell_volume || obj.outflow || 0);
      if (buy > 0 || sell > 0) {
        entries.push({ label: key, buy, sell });
      }
    } else if (typeof val === "number") {
      entries.push({
        label: key,
        buy: val > 0 ? val : 0,
        sell: val < 0 ? Math.abs(val) : 0,
      });
    }
  }

  if (entries.length === 0) {
    return (
      <Card>
        <CardHeader>Flow Intelligence</CardHeader>
        <div className="text-sm text-muted py-8 text-center">
          No flow breakdown available.
        </div>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>Flow Intelligence by Wallet Type</CardHeader>
      <ResponsiveContainer width="100%" height={Math.max(200, entries.length * 50)}>
        <BarChart data={entries} layout="vertical" margin={{ left: 10, right: 20 }}>
          <XAxis
            type="number"
            tickFormatter={(v: number) => fmtUsd(v)}
            tick={{ fill: "#737373", fontSize: 10, fontFamily: "monospace" }}
            stroke="#2a2a2a"
          />
          <YAxis
            type="category"
            dataKey="label"
            tick={{ fill: "#d4d4d4", fontSize: 11, fontFamily: "monospace" }}
            width={100}
            stroke="#2a2a2a"
          />
          <Tooltip
            formatter={(v) => fmtUsd(Number(v))}
            contentStyle={{
              background: "#1a1a1a",
              border: "1px solid #2a2a2a",
              borderRadius: 6,
              fontFamily: "monospace",
              fontSize: 12,
            }}
          />
          <Bar dataKey="buy" fill="#4ade80" name="Buy" radius={[0, 4, 4, 0]} />
          <Bar dataKey="sell" fill="#f43f5e" name="Sell" radius={[0, 4, 4, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </Card>
  );
}

function WhoBoughtSold({ data }: { data: Record<string, unknown> }) {
  // Parse who_bought_sold — may have buyers/sellers arrays or a flat structure
  const buyers = Array.isArray(data?.buyers)
    ? (data.buyers as Record<string, unknown>[])
    : [];
  const sellers = Array.isArray(data?.sellers)
    ? (data.sellers as Record<string, unknown>[])
    : [];

  if (buyers.length === 0 && sellers.length === 0) {
    return (
      <Card>
        <CardHeader>Who Bought / Sold</CardHeader>
        <div className="text-sm text-muted py-8 text-center">
          No buyer/seller data available.
        </div>
      </Card>
    );
  }

  function renderTable(
    rows: Record<string, unknown>[],
    side: "buy" | "sell"
  ) {
    const color = side === "buy" ? "text-bullish" : "text-bearish";
    return (
      <div className="overflow-x-auto">
        <table className="w-full text-xs font-mono">
          <thead>
            <tr className="text-muted border-b border-border">
              <th className="text-left py-1.5 px-2">Address</th>
              <th className="text-left py-1.5 px-2">Label</th>
              <th className="text-right py-1.5 px-2">Amount</th>
            </tr>
          </thead>
          <tbody>
            {rows.slice(0, 10).map((row, i) => {
              const addr = String(row.address || row.wallet || "");
              const label = String(
                row.label || row.entity || row.type || ""
              );
              const amount = Number(
                row.amount || row.volume || row.value || 0
              );
              return (
                <tr
                  key={i}
                  className="border-b border-border/50 hover:bg-surface-hover"
                >
                  <td className="py-1.5 px-2 text-muted">
                    {truncAddr(addr)}
                  </td>
                  <td className="py-1.5 px-2 text-white">
                    {label || "-"}
                  </td>
                  <td className={cn("py-1.5 px-2 text-right", color)}>
                    {fmtUsd(amount)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    );
  }

  return (
    <Card>
      <CardHeader>Who Bought / Sold</CardHeader>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-2">
        {buyers.length > 0 && (
          <div>
            <h4 className="text-xs font-mono font-bold text-bullish mb-1">
              BUYERS ({buyers.length})
            </h4>
            {renderTable(buyers, "buy")}
          </div>
        )}
        {sellers.length > 0 && (
          <div>
            <h4 className="text-xs font-mono font-bold text-bearish mb-1">
              SELLERS ({sellers.length})
            </h4>
            {renderTable(sellers, "sell")}
          </div>
        )}
      </div>
    </Card>
  );
}

function WalletProfiles({
  wallets,
}: {
  wallets: DeepDiveData["wallets"];
}) {
  if (!wallets || wallets.length === 0) {
    return (
      <Card>
        <CardHeader>Wallet Profiles</CardHeader>
        <div className="text-sm text-muted py-8 text-center">
          No profiled wallets available.
        </div>
      </Card>
    );
  }

  return (
    <div>
      <h3 className="font-mono font-bold text-sm text-muted mb-2">
        WALLET PROFILES ({wallets.length})
      </h3>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {wallets.slice(0, 12).map((w, i) => {
          const labels = w.labels ? Object.entries(w.labels) : [];
          const pnl = w.pnl_summary || {};
          const totalPnl = Number(
            (pnl as Record<string, unknown>).total_pnl ||
              (pnl as Record<string, unknown>).pnl ||
              (pnl as Record<string, unknown>).realized ||
              0
          );
          const winRate = Number(
            (pnl as Record<string, unknown>).win_rate ||
              (pnl as Record<string, unknown>).winrate ||
              0
          );

          return (
            <Card key={i}>
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-mono text-accent">
                  {truncAddr(w.address)}
                </span>
                {totalPnl !== 0 && (
                  <span
                    className={cn(
                      "text-xs font-mono font-bold",
                      totalPnl > 0 ? "text-bullish" : "text-bearish"
                    )}
                  >
                    {fmtUsd(totalPnl)}
                  </span>
                )}
              </div>

              {/* Labels */}
              {labels.length > 0 && (
                <div className="flex flex-wrap gap-1 mb-2">
                  {labels.map(([key, val]) => (
                    <span
                      key={key}
                      className="text-[10px] px-1.5 py-0.5 bg-surface-hover border border-border rounded font-mono text-muted"
                    >
                      {key}: {String(val)}
                    </span>
                  ))}
                </div>
              )}

              {/* PnL summary */}
              {(winRate > 0 || Object.keys(pnl).length > 0) && (
                <div className="text-[10px] font-mono text-muted space-y-0.5">
                  {winRate > 0 && <div>Win Rate: {winRate}%</div>}
                  {Object.entries(pnl)
                    .filter(
                      ([k]) =>
                        !["total_pnl", "pnl", "realized", "win_rate", "winrate"].includes(k)
                    )
                    .slice(0, 3)
                    .map(([k, v]) => (
                      <div key={k}>
                        {k}: {typeof v === "number" ? fmtUsd(v) : String(v)}
                      </div>
                    ))}
                </div>
              )}
            </Card>
          );
        })}
      </div>
    </div>
  );
}

function ExternalLinks({ chain, address }: { chain: string; address: string }) {
  const dexSlug = DEXSCREENER_SLUGS[chain] || chain;
  const dexUrl = `https://dexscreener.com/${dexSlug}/${address}`;
  const explorerBase = EXPLORER_URLS[chain];
  const explorerLabel = EXPLORER_LABELS[chain] || "Explorer";
  const explorerUrl = explorerBase ? `${explorerBase}${address}` : null;

  return (
    <div className="flex flex-wrap gap-3">
      <a
        href={dexUrl}
        target="_blank"
        rel="noopener noreferrer"
        className="flex items-center gap-1.5 px-3 py-1.5 bg-surface border border-border rounded text-sm font-mono text-accent hover:text-secondary hover:border-accent/30 transition"
      >
        <ExternalLink size={13} />
        DexScreener
      </a>
      {explorerUrl && (
        <a
          href={explorerUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1.5 px-3 py-1.5 bg-surface border border-border rounded text-sm font-mono text-accent hover:text-secondary hover:border-accent/30 transition"
        >
          <ExternalLink size={13} />
          {explorerLabel}
        </a>
      )}
    </div>
  );
}

function DeepDiveLoading() {
  return (
    <div className="space-y-4 animate-pulse">
      <div className="flex items-center gap-2 text-sm font-mono text-muted">
        <span className="w-2 h-2 rounded-full bg-accent animate-live" />
        Loading deep dive intelligence...
      </div>
      <ChartSkeleton height="h-48" />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <CardSkeleton />
        <CardSkeleton />
      </div>
      <ChartSkeleton height="h-32" />
    </div>
  );
}

function Indicators({ data }: { data: Record<string, unknown> }) {
  const entries = Object.entries(data);
  if (entries.length === 0) return null;

  return (
    <Card>
      <CardHeader>Indicators</CardHeader>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-2 mt-2">
        {entries.slice(0, 9).map(([key, val]) => (
          <div key={key} className="text-xs font-mono">
            <span className="text-muted">{key}:</span>{" "}
            <span className="text-white">
              {typeof val === "number"
                ? val > 1e3
                  ? fmtUsd(val)
                  : val.toFixed(2)
                : String(val ?? "-")}
            </span>
          </div>
        ))}
      </div>
    </Card>
  );
}

function DivergenceHistory({ chain, address }: { chain: string; address: string }) {
  const { data, isLoading } = useSWR<{ history: { scan_timestamp: string; divergence_strength: number; phase: string; price_usd: number }[] }>(
    `/api/token/${chain}/${address}/history?days=14`,
    fetcher,
    { revalidateOnFocus: false }
  );

  if (isLoading) return <ChartSkeleton height="h-48" />;
  if (!data?.history || data.history.length < 2) return null;

  const chartData = data.history.map((h) => ({
    time: new Date(h.scan_timestamp).toLocaleDateString(undefined, { month: "short", day: "numeric" }),
    strength: h.divergence_strength,
    price: h.price_usd,
  }));

  return (
    <Card>
      <CardHeader>Divergence Strength (14d)</CardHeader>
      <ResponsiveContainer width="100%" height={200}>
        <AreaChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="divGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#f97316" stopOpacity={0.4} />
              <stop offset="95%" stopColor="#f97316" stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis dataKey="time" tick={{ fill: "#737373", fontSize: 10, fontFamily: "monospace" }} stroke="#2a2a2a" />
          <YAxis tick={{ fill: "#737373", fontSize: 10, fontFamily: "monospace" }} stroke="#2a2a2a" domain={[0, 1]} />
          <Tooltip
            contentStyle={{ background: "#1a1a1a", border: "1px solid #2a2a2a", borderRadius: 6, fontFamily: "monospace", fontSize: 12 }}
            formatter={(v: number) => [v.toFixed(2), "Strength"]}
          />
          <Area type="monotone" dataKey="strength" stroke="#f97316" fill="url(#divGrad)" strokeWidth={2} />
        </AreaChart>
      </ResponsiveContainer>
    </Card>
  );
}

/* ---------- main page ---------- */

interface SummaryResponse {
  token: Token;
  timestamp: string;
}

export default function TokenPage({
  params,
}: {
  params: Promise<{ chain: string; address: string }>;
}) {
  const { chain, address } = use(params);

  // Instant summary from cache
  const {
    data: summaryData,
    error: summaryError,
    isLoading: summaryLoading,
  } = useSWR<SummaryResponse>(
    `/api/token/${chain}/${address}/summary`,
    fetcher,
    { revalidateOnFocus: false }
  );

  // Slower deep dive
  const {
    data: deepDive,
    error: deepError,
    isLoading: deepLoading,
  } = useSWR<DeepDiveData>(
    `/api/token/${chain}/${address}`,
    fetcher,
    { revalidateOnFocus: false }
  );

  const token = summaryData?.token;

  return (
    <main className="max-w-7xl mx-auto px-4 py-4">
      {/* Back link */}
      <Link
        href="/"
        className="inline-flex items-center gap-1.5 text-sm font-mono text-muted hover:text-accent transition mb-4"
      >
        <ArrowLeft size={14} />
        Back to Dashboard
      </Link>

      {/* Summary loading */}
      {summaryLoading && (
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <Skeleton className="h-8 w-32" />
            <Skeleton className="h-5 w-20" />
            <Skeleton className="h-5 w-16" />
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <CardSkeleton />
            <CardSkeleton />
            <CardSkeleton />
            <CardSkeleton />
          </div>
        </div>
      )}

      {/* Summary error */}
      {summaryError && (
        <div className="bg-surface border border-bearish rounded-lg p-4 font-mono text-sm text-bearish">
          Failed to load token summary. The token may not exist in the latest scan.
        </div>
      )}

      {/* Summary loaded */}
      {token && (
        <>
          <SummarySection token={token} />

          {/* Historical divergence chart */}
          <div className="mt-4">
            <DivergenceHistory chain={chain} address={address} />
          </div>

          {/* External links */}
          <div className="mt-4">
            <ExternalLinks chain={chain} address={address} />
          </div>

          {/* SM donut + deep dive flow side by side */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-6">
            <SMDonut token={token} />

            {/* Flow Intelligence — from deep dive */}
            {deepLoading && <ChartSkeleton height="h-64" />}
            {deepDive?.flow_intelligence &&
              Object.keys(deepDive.flow_intelligence).length > 0 && (
                <FlowIntelligence flowData={deepDive.flow_intelligence} />
              )}
            {!deepLoading &&
              deepDive &&
              (!deepDive.flow_intelligence ||
                Object.keys(deepDive.flow_intelligence).length === 0) && (
                <Card>
                  <CardHeader>Flow Intelligence</CardHeader>
                  <div className="text-sm text-muted py-8 text-center">
                    No flow breakdown available.
                  </div>
                </Card>
              )}
          </div>

          {/* Deep dive sections */}
          <div className="mt-6 space-y-6">
            {deepLoading && <DeepDiveLoading />}

            {deepError && !deepLoading && (
              <div className="bg-surface border border-border rounded-lg p-4 font-mono text-sm text-muted">
                Deep dive data unavailable. Summary data shown above.
              </div>
            )}

            {deepDive && (
              <div className="space-y-6 animate-fade-in">
                {/* Indicators */}
                {deepDive.indicators &&
                  Object.keys(deepDive.indicators).length > 0 && (
                    <Indicators data={deepDive.indicators} />
                  )}

                {/* Who bought/sold */}
                {deepDive.who_bought_sold && (
                  <WhoBoughtSold data={deepDive.who_bought_sold} />
                )}

                {/* Wallet Profiles */}
                {deepDive.wallets && (
                  <WalletProfiles wallets={deepDive.wallets} />
                )}
              </div>
            )}
          </div>
        </>
      )}
    </main>
  );
}
