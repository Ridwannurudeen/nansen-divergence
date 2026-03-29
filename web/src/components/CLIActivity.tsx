"use client";

import useSWR from "swr";
import { fetcher } from "@/lib/api";
import { Terminal } from "lucide-react";

interface CLIEntry {
  command: string;
  endpoint: string;
  chain: string;
  credits: number;
  success: boolean;
  token_count: number;
  source: string;
  timestamp: string;
}

interface CLIStats {
  total_calls: number;
  total_credits: number;
  endpoints_used: string[];
  endpoints_count: number;
  calls_success: number;
  last_call_at: string | null;
}

function timeAgo(ts: string): string {
  const diff = (Date.now() - new Date(ts).getTime()) / 1000;
  if (diff < 60) return `${Math.floor(diff)}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

function SourceBadge({ source }: { source: string }) {
  const cls = source === "cli" ? "bg-bullish text-bg" : source === "rest" ? "bg-accent text-bg" : "bg-border text-muted";
  return <span className={`text-xs px-1 rounded font-bold uppercase ${cls}`}>{source}</span>;
}

export function CLIActivity() {
  const { data: activityData } = useSWR<{ activity: CLIEntry[] }>(
    "/api/cli/activity",
    fetcher,
    { refreshInterval: 15000 }
  );
  const { data: statsData } = useSWR<CLIStats>(
    "/api/cli/stats",
    fetcher,
    { refreshInterval: 15000 }
  );

  const activity = activityData?.activity || [];
  const stats = statsData;

  return (
    <div className="bg-surface border border-border rounded-lg overflow-hidden">
      <div className="flex items-center justify-between px-3 py-2 border-b border-border bg-bg">
        <div className="flex items-center gap-2">
          <Terminal size={14} className="text-bullish" />
          <span className="font-mono font-bold text-sm text-white">NANSEN CLI ACTIVITY</span>
        </div>
        {stats && (
          <div className="flex items-center gap-3 text-xs font-mono">
            <span className="text-bullish">{stats.total_calls} calls</span>
            <span className="text-accent">{stats.total_credits} credits</span>
            <span className="text-secondary">{stats.endpoints_count} endpoints</span>
          </div>
        )}
      </div>

      <div className="max-h-[280px] overflow-y-auto">
        {activity.length === 0 ? (
          <div className="p-4 text-center text-muted text-sm font-mono">
            <div className="animate-pulse">Waiting for CLI activity...</div>
            <div className="text-xs mt-1">CLI enrichment runs every 30 minutes</div>
          </div>
        ) : (
          <div className="divide-y divide-border/30">
            {activity.slice(0, 20).map((entry, i) => (
              <div key={i} className="px-3 py-1.5 hover:bg-surface-hover transition-colors">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2 min-w-0 flex-1">
                    <span className="w-1.5 h-1.5 rounded-full flex-shrink-0 bg-bullish" />
                    <SourceBadge source={entry.source} />
                    <span className="text-xs font-mono text-white truncate">{entry.endpoint}</span>
                    <span className="text-xs font-mono text-muted">{entry.chain}</span>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    {entry.token_count > 0 && (
                      <span className="text-xs font-mono text-secondary">{entry.token_count} tokens</span>
                    )}
                    {entry.credits > 0 && (
                      <span className="text-xs font-mono text-accent">{entry.credits}cr</span>
                    )}
                    <span className="text-xs font-mono text-muted">{timeAgo(entry.timestamp)}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {stats && stats.endpoints_used.length > 0 && (
        <div className="px-3 py-2 border-t border-border bg-bg">
          <div className="flex flex-wrap gap-1">
            {stats.endpoints_used.map((ep) => (
              <span key={ep} className="text-xs font-mono bg-surface px-1.5 py-0.5 rounded text-muted">{ep}</span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
