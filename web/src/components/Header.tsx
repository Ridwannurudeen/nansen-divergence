"use client";

import { useState, useEffect } from "react";

function relativeTime(ts: string): string {
  const diff = Math.floor((Date.now() - new Date(ts).getTime()) / 1000);
  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

interface HeaderProps {
  timestamp?: string;
  isDemo?: boolean;
}

export function Header({ timestamp, isDemo }: HeaderProps) {
  const [rel, setRel] = useState("");

  useEffect(() => {
    if (!timestamp) return;
    setRel(relativeTime(timestamp));
    const iv = setInterval(() => setRel(relativeTime(timestamp)), 30000);
    return () => clearInterval(iv);
  }, [timestamp]);

  const time = timestamp ? new Date(timestamp).toLocaleTimeString() : "---";
  const date = timestamp ? new Date(timestamp).toLocaleDateString() : "";
  return (
    <header className="py-4">
      {isDemo && (
        <div className="bg-accent/10 border border-accent/30 text-accent font-mono text-xs px-3 py-1.5 rounded mb-3 text-center">
          DEMO DATA — waiting for live scan. Results refresh automatically.
        </div>
      )}
      <div className="flex items-center justify-between">
      <div>
        <h1 className="text-xl font-mono font-bold text-accent glow-orange">SMART MONEY DIVERGENCE</h1>
        <p className="text-xs text-muted font-mono">Multi-chain Wyckoff phase detection via volume proxy analysis</p>
      </div>
      <div className="text-right text-xs text-muted font-mono">
        <div className="flex items-center gap-2 justify-end">
          <span className="w-1.5 h-1.5 rounded-full bg-bullish animate-live" />
          Last scan: {time}
        </div>
        {rel && <div className="text-accent">{rel}</div>}
        {date && <div className="text-muted/50">{date}</div>}
      </div>
      </div>
    </header>
  );
}
