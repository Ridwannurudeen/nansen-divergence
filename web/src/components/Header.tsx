interface HeaderProps {
  timestamp?: string;
}

export function Header({ timestamp }: HeaderProps) {
  const time = timestamp ? new Date(timestamp).toLocaleTimeString() : "---";
  const date = timestamp ? new Date(timestamp).toLocaleDateString() : "";
  return (
    <header className="flex items-center justify-between py-4">
      <div>
        <h1 className="text-xl font-mono font-bold text-accent glow-orange">SMART MONEY DIVERGENCE</h1>
        <p className="text-xs text-muted font-mono">Multi-chain Wyckoff phase detection via Nansen SM data</p>
      </div>
      <div className="text-right text-xs text-muted font-mono">
        <div className="flex items-center gap-2 justify-end">
          <span className="w-1.5 h-1.5 rounded-full bg-bullish animate-live" />
          Last scan: {time}
        </div>
        {date && <div className="text-muted/50">{date}</div>}
      </div>
    </header>
  );
}
