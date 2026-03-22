import { ScanSummary, BacktestStats } from "@/lib/types";

interface MetricCardsProps {
  summary: ScanSummary;
  backtest: BacktestStats;
  avgAlpha: number;
}

function Card({ label, value, color }: { label: string; value: string | number; color?: string }) {
  return (
    <div className="bg-surface border border-border rounded-lg p-4">
      <div className="text-xs font-mono text-muted uppercase tracking-wider">{label}</div>
      <div className={`text-2xl font-mono font-bold mt-1 ${color || "text-accent"}`}>{value}</div>
    </div>
  );
}

export function MetricCards({ summary, backtest, avgAlpha }: MetricCardsProps) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3 py-4">
      <Card label="Tokens" value={summary.total_tokens} />
      <Card label="Divergence" value={summary.divergence_signals} />
      <Card label="Win Rate" value={backtest.total_signals > 0 ? `${backtest.win_rate}%` : "N/A"} color="text-bullish" />
      <Card label="HIGH" value={summary.confidence_high} color="text-bullish" />
      <Card label="MEDIUM" value={summary.confidence_medium} color="text-secondary" />
      <Card label="Avg Alpha" value={avgAlpha} />
    </div>
  );
}
