import { Token } from "@/lib/types";

const PHASE_COLORS: Record<string, string> = {
  ACCUMULATION: "border-bullish",
  DISTRIBUTION: "border-bearish",
  MARKUP: "border-neutral",
  MARKDOWN: "border-warning",
};

const CONF_STYLES: Record<string, string> = {
  HIGH: "bg-bullish text-bg",
  MEDIUM: "bg-accent text-bg",
  LOW: "bg-surface text-muted",
};

interface StreakData {
  phase: string;
  streak: number;
  since: string;
}

interface SignalFeedProps {
  results: Token[];
  streaks?: Record<string, StreakData>;
}

export function SignalFeed({ results, streaks }: SignalFeedProps) {
  const signals = results
    .filter((r) => ["ACCUMULATION", "DISTRIBUTION"].includes(r.phase) && ["HIGH", "MEDIUM"].includes(r.confidence))
    .sort((a, b) => b.divergence_strength - a.divergence_strength)
    .slice(0, 15);

  if (signals.length === 0) {
    return <div className="text-muted text-sm font-mono py-4">No divergence signals detected.</div>;
  }

  return (
    <div className="space-y-2 max-h-[420px] overflow-y-auto pr-1 sm:pr-2" role="list" aria-label="Divergence signals">
      {signals.map((t, i) => {
        const streak = streaks?.[t.token_address.toLowerCase()];
        return (
          <div
            key={`${t.chain}-${t.token_address}-${i}`}
            className={`border-l-4 ${PHASE_COLORS[t.phase]} bg-surface rounded-r px-2 sm:px-3 py-2 animate-slide-up`}
            style={{ animationDelay: `${i * 50}ms`, animationFillMode: "backwards" }}
            role="listitem"
          >
            <div className="flex flex-wrap items-center gap-1.5 sm:gap-2 text-sm font-mono">
              <span className="font-bold text-white">{t.token_symbol}</span>
              <span className="text-muted text-xs">{t.chain.slice(0, 3).toUpperCase()}</span>
              <span className={`text-xs px-1.5 py-0.5 rounded ${CONF_STYLES[t.confidence]}`}>
                {t.phase === "ACCUMULATION" ? "ACC" : "DIS"}
              </span>
              {streak && streak.streak >= 2 && (
                <span className="text-xs px-1.5 py-0.5 rounded bg-accent/20 text-accent font-bold">
                  {streak.streak}x
                </span>
              )}
              <span className="text-accent font-bold ml-auto sm:ml-0">a{t.alpha_score}</span>
              <span className={t.price_change > 0 ? "text-bullish" : "text-bearish"}>
                {t.price_change > 0 ? "+" : ""}{(t.price_change * 100).toFixed(1)}%
              </span>
            </div>
            {t.narrative && <div className="text-xs text-muted mt-1 italic">{t.narrative}</div>}
          </div>
        );
      })}
    </div>
  );
}
