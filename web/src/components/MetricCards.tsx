import { ScanSummary, BacktestStats } from "@/lib/types";
import { Card, CardHeader, CardValue } from "@/components/ui/Card";
import { cn } from "@/lib/utils";

interface MetricCardsProps {
  summary: ScanSummary;
  backtest: BacktestStats;
  avgAlpha: number;
}

function Metric({ label, value, color, glow }: { label: string; value: string | number; color?: string; glow?: string }) {
  return (
    <Card>
      <CardHeader>{label}</CardHeader>
      <CardValue className={cn(color || "text-accent", glow)}>{value}</CardValue>
    </Card>
  );
}

export function MetricCards({ summary, backtest, avgAlpha }: MetricCardsProps) {
  const winRate = backtest.total_signals > 0 ? `${backtest.win_rate}%` : "---";
  const avgReturn = backtest.total_signals > 0 ? `${backtest.avg_return > 0 ? "+" : ""}${backtest.avg_return}%` : "---";

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-2 sm:gap-3 py-4">
      <Metric label="Tokens" value={summary.total_tokens} />
      <Metric label="Vol Activity" value={`${summary.sm_data_pct}%`} color="text-secondary" />
      <Metric label="Signals" value={summary.divergence_signals} color="text-accent" glow="glow-orange" />
      <Metric label="Win Rate" value={winRate} color="text-bullish" glow="glow-green" />
      <Metric
        label="Avg Return"
        value={avgReturn}
        color={backtest.avg_return >= 0 ? "text-bullish" : "text-bearish"}
        glow={backtest.avg_return >= 0 ? "glow-green" : "glow-red"}
      />
      <Metric label="Best" value={backtest.total_signals > 0 ? `${backtest.best_return > 0 ? "+" : ""}${backtest.best_return}%` : "---"} color="text-bullish" glow="glow-green" />
      <Metric label="Worst" value={backtest.total_signals > 0 ? `${backtest.worst_return}%` : "---"} color="text-bearish" glow="glow-red" />
      <Metric label="HIGH Conf" value={summary.confidence_high} color="text-bullish" />
      <Metric label="CLI Enriched" value={summary.cli_enriched_count ?? 0} color="text-secondary" />
      <Metric label="Avg Alpha" value={avgAlpha} color="text-accent" glow="glow-orange" />
      <Metric label="ACC / DIS" value={`${summary.accumulation} / ${summary.distribution}`} />
    </div>
  );
}
