"use client";

import { useState } from "react";
import Link from "next/link";
import { Token } from "@/lib/types";
import { fmtUsd, DEXSCREENER_SLUGS, cn } from "@/lib/utils";

const PHASE_ORDER = ["ACCUMULATION", "DISTRIBUTION", "MARKUP", "MARKDOWN"] as const;
const PHASE_LABELS: Record<string, { label: string; color: string; desc: string; bg: string }> = {
  ACCUMULATION: { label: "ACCUMULATION", color: "text-bullish", desc: "SM buying into price weakness", bg: "bg-bullish" },
  DISTRIBUTION: { label: "DISTRIBUTION", color: "text-bearish", desc: "SM exiting into price strength", bg: "bg-bearish" },
  MARKUP: { label: "MARKUP", color: "text-neutral", desc: "Trend confirmed", bg: "bg-neutral" },
  MARKDOWN: { label: "MARKDOWN", color: "text-warning", desc: "Capitulation", bg: "bg-warning" },
};

const SPARK_COLORS: Record<string, string> = {
  ACCUMULATION: "#22c55e",
  DISTRIBUTION: "#ef4444",
  MARKUP: "#6366f1",
  MARKDOWN: "#f59e0b",
};

const PHASE_BORDER: Record<string, string> = {
  ACCUMULATION: "border-l-bullish",
  DISTRIBUTION: "border-l-bearish",
  MARKUP: "border-l-neutral",
  MARKDOWN: "border-l-warning",
};

function Sparkline({ data, phase }: { data: number[]; phase: string }) {
  if (!data || data.length < 2) return <span className="text-muted text-xs">--</span>;
  const w = 60, h = 20;
  const max = Math.max(...data, 0.01);
  const min = Math.min(...data, 0);
  const range = max - min || 1;
  const points = data.map((v, i) => `${(i / (data.length - 1)) * w},${h - ((v - min) / range) * h}`).join(" ");
  const color = SPARK_COLORS[phase] || "#f97316";
  return (
    <svg width={w} height={h} className="inline-block" role="img" aria-label="Divergence trend sparkline">
      <polyline points={points} fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function AlphaBar({ score }: { score: number }) {
  const color = score >= 70 ? "#f43f5e" : score >= 40 ? "#f97316" : "#6366f1";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-border rounded-full overflow-hidden">
        <div className="h-full rounded-full transition-all" style={{ width: `${score}%`, backgroundColor: color }} />
      </div>
      <span className="text-xs font-mono font-bold" style={{ color }}>{score}</span>
    </div>
  );
}

function ConfPill({ confidence }: { confidence: string }) {
  const cls = confidence === "HIGH" ? "bg-bullish text-bg" : confidence === "MEDIUM" ? "bg-accent text-bg" : "bg-border text-muted";
  return <span className={`text-xs px-2 py-0.5 rounded font-mono font-bold ${cls}`}>{confidence}</span>;
}

/* ── Mobile card for a single token ── */
function TokenCard({ t, sparkData }: { t: Token; sparkData?: number[] }) {
  const flow = t.sm_net_flow !== 0 ? t.sm_net_flow : t.market_netflow;
  const slug = DEXSCREENER_SLUGS[t.chain] || t.chain;
  const dexUrl = `https://dexscreener.com/${slug}/${t.token_address}`;

  return (
    <div className={cn(
      "bg-surface border border-border/50 rounded-lg p-3 border-l-4",
      PHASE_BORDER[t.phase] || "border-l-muted",
    )}>
      {/* Row 1: Symbol, chain, confidence, chart link */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Link href={`/token/${t.chain}/${t.token_address}`} className="text-white font-bold font-mono hover:text-accent transition-colors">
            {t.token_symbol}
          </Link>
          {t.is_new && <span className="text-xs bg-bearish text-white px-1 rounded">NEW</span>}
          <span className="text-muted text-xs font-mono">{t.chain.toUpperCase()}</span>
        </div>
        <div className="flex items-center gap-2">
          <ConfPill confidence={t.confidence} />
          <a href={dexUrl} target="_blank" rel="noopener noreferrer" className="text-accent hover:text-secondary text-xs font-mono focus-visible:outline-accent" aria-label={`View ${t.token_symbol} on DexScreener`}>
            Chart
          </a>
        </div>
      </div>

      {/* Row 2: Price change + sparkline */}
      <div className="flex items-center justify-between mb-2">
        <span className={cn("text-sm font-mono font-bold", t.price_change > 0 ? "text-bullish" : "text-bearish")}>
          {t.price_change > 0 ? "+" : ""}{(t.price_change * 100).toFixed(1)}%
        </span>
        <Sparkline data={sparkData || []} phase={t.phase} />
      </div>

      {/* Row 3: Flow, Buy, Sell in a 3-col grid */}
      <div className="grid grid-cols-3 gap-2 text-xs font-mono mb-2">
        <div>
          <div className="text-muted">Flow</div>
          <div className={flow > 0 ? "text-bullish font-bold" : "text-bearish font-bold"}>{fmtUsd(flow)}</div>
        </div>
        <div>
          <div className="text-muted">Buy</div>
          <div className="text-bullish">{fmtUsd(t.sm_buy_volume)}</div>
        </div>
        <div>
          <div className="text-muted">Sell</div>
          <div className="text-bearish">{fmtUsd(t.sm_sell_volume)}</div>
        </div>
      </div>

      {/* Row 4: Alpha bar */}
      <AlphaBar score={t.alpha_score} />
    </div>
  );
}

interface TokenTableProps {
  results: Token[];
  sparklines?: Record<string, number[]>;
}

export function TokenTable({ results, sparklines }: TokenTableProps) {
  const [activePhase, setActivePhase] = useState<string | null>(null);

  const grouped: Record<string, Token[]> = {};
  for (const p of PHASE_ORDER) grouped[p] = [];
  for (const r of results) {
    if (grouped[r.phase]) grouped[r.phase].push(r);
  }
  for (const p of PHASE_ORDER) {
    grouped[p].sort((a, b) => b.divergence_strength - a.divergence_strength);
  }

  const phases = activePhase ? [activePhase] : [...PHASE_ORDER];

  return (
    <div>
      {/* Phase filter buttons — horizontally scrollable on mobile */}
      <div className="flex gap-2 py-3 border-b border-border mb-4 overflow-x-auto scrollbar-none">
        <button
          onClick={() => setActivePhase(null)}
          className={cn(
            "px-3 py-1 rounded text-sm font-mono whitespace-nowrap transition-colors focus-visible:outline-2 focus-visible:outline-accent",
            !activePhase ? "bg-accent text-bg" : "bg-surface text-muted hover:text-white hover:bg-surface-hover",
          )}
        >
          ALL
        </button>
        {PHASE_ORDER.map((p) => {
          const info = PHASE_LABELS[p];
          const count = grouped[p].length;
          if (count === 0) return null;
          return (
            <button
              key={p}
              onClick={() => setActivePhase(activePhase === p ? null : p)}
              className={cn(
                "flex items-center gap-1.5 px-3 py-1 rounded text-sm font-mono whitespace-nowrap transition-colors focus-visible:outline-2 focus-visible:outline-accent",
                activePhase === p ? "bg-accent text-bg" : "bg-surface text-muted hover:text-white hover:bg-surface-hover",
              )}
            >
              <span className={info.color}>{info.label}</span>
              <span className={`${info.bg} text-bg text-xs px-1.5 py-0.5 rounded-full font-bold min-w-[20px] text-center`}>{count}</span>
            </button>
          );
        })}
      </div>

      {phases.map((phase) => {
        const tokens = grouped[phase];
        if (!tokens || tokens.length === 0) return null;
        const info = PHASE_LABELS[phase];

        return (
          <div key={phase} className="mb-6">
            <h3 className={`font-mono font-bold text-sm mb-2 ${info.color}`}>
              {info.label} — <span className="text-muted font-normal">{info.desc}</span> ({tokens.length})
            </h3>

            {/* Mobile: card layout */}
            <div className="md:hidden space-y-2">
              {tokens.map((t, i) => (
                <TokenCard key={`${t.chain}-${t.token_address}-${i}`} t={t} sparkData={sparklines?.[t.token_address.toLowerCase()]} />
              ))}
            </div>

            {/* Desktop: table layout */}
            <div className="hidden md:block overflow-x-auto">
              <table className="w-full text-sm font-mono">
                <thead>
                  <tr className="text-muted text-xs border-b border-border">
                    <th className="text-left py-2 px-2">Token</th>
                    <th className="text-left py-2 px-2">Chain</th>
                    <th className="text-center py-2 px-2">Trend</th>
                    <th className="text-right py-2 px-2">Price</th>
                    <th className="text-right py-2 px-2">Flow</th>
                    <th className="text-right py-2 px-2 hidden lg:table-cell">Buy</th>
                    <th className="text-right py-2 px-2 hidden lg:table-cell">Sell</th>
                    <th className="text-left py-2 px-2 w-32">Alpha</th>
                    <th className="text-center py-2 px-2">Conf</th>
                    <th className="text-center py-2 px-2">Chart</th>
                  </tr>
                </thead>
                <tbody>
                  {tokens.map((t, i) => {
                    const flow = t.sm_net_flow !== 0 ? t.sm_net_flow : t.market_netflow;
                    const slug = DEXSCREENER_SLUGS[t.chain] || t.chain;
                    const dexUrl = `https://dexscreener.com/${slug}/${t.token_address}`;
                    const sparkData = sparklines?.[t.token_address.toLowerCase()];
                    return (
                      <tr key={`${t.chain}-${t.token_address}-${i}`} className="border-b border-border/50 hover:bg-surface-hover transition-colors">
                        <td className="py-2 px-2">
                          <Link href={`/token/${t.chain}/${t.token_address}`} className="text-white font-bold hover:text-accent transition-colors focus-visible:outline-accent">
                            {t.token_symbol}
                          </Link>
                          {t.is_new && <span className="ml-1 text-xs bg-bearish text-white px-1 rounded">NEW</span>}
                        </td>
                        <td className="py-2 px-2 text-muted">{t.chain}</td>
                        <td className="py-2 px-2 text-center">
                          <Sparkline data={sparkData || []} phase={t.phase} />
                        </td>
                        <td className={`py-2 px-2 text-right ${t.price_change > 0 ? "text-bullish" : "text-bearish"}`}>
                          {t.price_change > 0 ? "+" : ""}{(t.price_change * 100).toFixed(1)}%
                        </td>
                        <td className={`py-2 px-2 text-right ${flow > 0 ? "text-bullish" : "text-bearish"}`}>
                          {fmtUsd(flow)}
                        </td>
                        <td className="py-2 px-2 text-right text-bullish hidden lg:table-cell">{fmtUsd(t.sm_buy_volume)}</td>
                        <td className="py-2 px-2 text-right text-bearish hidden lg:table-cell">{fmtUsd(t.sm_sell_volume)}</td>
                        <td className="py-2 px-2"><AlphaBar score={t.alpha_score} /></td>
                        <td className="py-2 px-2 text-center"><ConfPill confidence={t.confidence} /></td>
                        <td className="py-2 px-2 text-center">
                          <a href={dexUrl} target="_blank" rel="noopener noreferrer" className="text-accent hover:text-secondary transition-colors focus-visible:outline-accent" onClick={(e) => e.stopPropagation()} aria-label={`View ${t.token_symbol} on DexScreener`}>
                            View
                          </a>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        );
      })}
    </div>
  );
}
