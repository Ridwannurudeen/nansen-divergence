interface HeaderProps {
  timestamp?: string;
}

export function Header({ timestamp }: HeaderProps) {
  const time = timestamp ? new Date(timestamp).toLocaleTimeString() : "—";
  return (
    <header className="flex items-center justify-between py-4 border-b border-border">
      <div>
        <h1 className="text-2xl font-mono font-bold text-accent">SM DIVERGENCE</h1>
        <p className="text-sm text-muted">Smart Money vs Price — Who's Right?</p>
      </div>
      <div className="text-right text-sm text-muted font-mono">
        <div>Last scan: {time}</div>
      </div>
    </header>
  );
}
