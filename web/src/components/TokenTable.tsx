"use client";

import { useState } from "react";
import Link from "next/link";
import { Token } from "@/lib/types";
import { fmtUsd, DEXSCREENER_SLUGS } from "@/lib/utils";

const PHASE_ORDER = ["ACCUMULATION", "DISTRIBUTION", "MARKUP", "MARKDOWN"] as const;
const PHASE_LABELS: Record<string, { label: string; color: string; desc: string }> = {
  ACCUMULATION: { label: "ACCUMULATION", color: "text-bullish", desc: "SM buying into price weakness" },
  DISTRIBUTION: { label: "DISTRIBUTION", color: "text-bearish", desc: "SM exiting into price strength" },
  MARKUP: { label: "MARKUP", color: "text-neutral", desc: "Trend confirmed" },
  MARKDOWN: { label: "MARKDOWN", color: "text-warning", desc: "Capitulation" },
};

function AlphaBar({ score }: { score: number }) {
  const color = score >= 70 ? "#f43f5e" : score >= 40 ? "#f97316" : "#6366f1";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-border rounded-full overflow-hidden">
        <div className="h-full rounded-full" style={{ width: `${score}%`, backgroundColor: color }} />
      </div>
      <span className="text-xs font-mono font-bold" style={{ color }}>{score}</span>
    </div>
  );
}

function ConfPill({ confidence }: { confidence: string }) {
  const cls = confidence === "HIGH" ? "bg-bullish text-bg" : confidence === "MEDIUM" ? "bg-accent text-bg" : "bg-border text-muted";
  return <span className={`text-xs px-2 py-0.5 rounded font-mono font-bold ${cls}`}>{confidence}</span>;
}

interface TokenTableProps {
  results: Token[];
}

export function TokenTable({ results }: TokenTableProps) {
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
      <div className="flex gap-2 py-3 border-b border-border mb-4">
        <button
          onClick={() => setActivePhase(null)}
          className={`px-3 py-1 rounded text-sm font-mono ${!activePhase ? "bg-accent text-bg" : "bg-surface text-muted hover:text-white"}`}
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
              className={`px-3 py-1 rounded text-sm font-mono ${activePhase === p ? "bg-accent text-bg" : "bg-surface text-muted hover:text-white"}`}
            >
              <span className={info.color}>{info.label}</span> ({count})
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
            <div className="overflow-x-auto">
              <table className="w-full text-sm font-mono">
                <thead>
                  <tr className="text-muted text-xs border-b border-border">
                    <th className="text-left py-2 px-2">Token</th>
                    <th className="text-left py-2 px-2">Chain</th>
                    <th className="text-right py-2 px-2">Price</th>
                    <th className="text-right py-2 px-2">Flow</th>
                    <th className="text-right py-2 px-2">Buy</th>
                    <th className="text-right py-2 px-2">Sell</th>
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
                    return (
                      <tr key={`${t.chain}-${t.token_address}-${i}`} className="border-b border-border/50 hover:bg-surface/50 cursor-pointer">
                        <td className="py-2 px-2">
                          <Link href={`/token/${t.chain}/${t.token_address}`} className="text-white font-bold hover:text-accent">
                            {t.token_symbol}
                          </Link>
                          {t.is_new && <span className="ml-1 text-xs bg-bearish text-white px-1 rounded">NEW</span>}
                        </td>
                        <td className="py-2 px-2 text-muted">{t.chain}</td>
                        <td className={`py-2 px-2 text-right ${t.price_change > 0 ? "text-bullish" : "text-bearish"}`}>
                          {t.price_change > 0 ? "+" : ""}{(t.price_change * 100).toFixed(1)}%
                        </td>
                        <td className={`py-2 px-2 text-right ${flow > 0 ? "text-bullish" : "text-bearish"}`}>
                          {fmtUsd(flow)}
                        </td>
                        <td className="py-2 px-2 text-right text-bullish">{fmtUsd(t.sm_buy_volume)}</td>
                        <td className="py-2 px-2 text-right text-bearish">{fmtUsd(t.sm_sell_volume)}</td>
                        <td className="py-2 px-2"><AlphaBar score={t.alpha_score} /></td>
                        <td className="py-2 px-2 text-center"><ConfPill confidence={t.confidence} /></td>
                        <td className="py-2 px-2 text-center">
                          <a href={dexUrl} target="_blank" rel="noopener noreferrer" className="text-accent hover:text-secondary" onClick={(e) => e.stopPropagation()}>
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
