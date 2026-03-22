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
  const winRate = backtest.total_signals > 0 ? `${backtest.win_rate}%` : "N/A";
  const avgReturn = backtest.total_signals > 0 ? `${backtest.avg_return > 0 ? "+" : ""}${backtest.avg_return}%` : "N/A";

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3 py-4">
      <Metric label="Tokens" value={summary.total_tokens} />
      <Metric label="SM Coverage" value={`${summary.sm_data_pct}%`} color="text-secondary" />
      <Metric label="Signals" value={summary.divergence_signals} color="text-accent" />
      <Metric label="Win Rate" value={winRate} color="text-bullish" glow="glow-green" />
      <Metric
        label="Avg Return"
        value={avgReturn}
        color={backtest.avg_return >= 0 ? "text-bullish" : "text-bearish"}
        glow={backtest.avg_return >= 0 ? "glow-green" : "glow-red"}
      />
      <Metric label="Best" value={`${backtest.best_return > 0 ? "+" : ""}${backtest.best_return}%`} color="text-bullish" />
      <Metric label="Worst" value={`${backtest.worst_return}%`} color="text-bearish" />
      <Metric label="HIGH Conf" value={summary.confidence_high} color="text-bullish" />
      <Metric label="Avg Alpha" value={avgAlpha} />
      <Metric label="ACC / DIS" value={`${summary.accumulation} / ${summary.distribution}`} />
    </div>
  );
}
