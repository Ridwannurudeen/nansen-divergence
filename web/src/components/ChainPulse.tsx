import { Token } from "@/lib/types";

const CHAINS = [
  { id: "ethereum", label: "ETH" },
  { id: "bnb", label: "BNB" },
  { id: "solana", label: "SOL" },
  { id: "base", label: "BASE" },
  { id: "arbitrum", label: "ARB" },
  { id: "polygon", label: "POL" },
  { id: "optimism", label: "OP" },
  { id: "avalanche", label: "AVAX" },
  { id: "linea", label: "LNA" },
];

interface ChainPulseProps {
  results: Token[];
  scannedChains: string[];
  activeChain: string | null;
  onChainClick: (chain: string | null) => void;
}

export function ChainPulse({ results, scannedChains, activeChain, onChainClick }: ChainPulseProps) {
  const chainPhases: Record<string, { acc: number; dis: number }> = {};
  for (const r of results) {
    if (!chainPhases[r.chain]) chainPhases[r.chain] = { acc: 0, dis: 0 };
    if (r.phase === "ACCUMULATION") chainPhases[r.chain].acc++;
    else if (r.phase === "DISTRIBUTION") chainPhases[r.chain].dis++;
  }

  return (
    <div className="flex gap-2 sm:gap-3 py-3 overflow-x-auto scrollbar-none" role="group" aria-label="Filter by blockchain">
      <button
        onClick={() => onChainClick(null)}
        className={`px-3 py-1 rounded text-sm font-mono whitespace-nowrap transition-colors ${
          activeChain === null ? "bg-accent text-bg" : "bg-surface text-muted hover:text-white hover:bg-surface-hover"
        }`}
      >
        ALL
      </button>
      {CHAINS.map(({ id, label }) => {
        const scanned = scannedChains.includes(id);
        const p = chainPhases[id];
        const dotColor = !scanned
          ? "bg-muted"
          : p && p.acc > p.dis
          ? "bg-bullish"
          : p && p.dis > p.acc
          ? "bg-bearish"
          : "bg-muted";
        const isActive = activeChain === id;

        return (
          <button
            key={id}
            onClick={() => onChainClick(isActive ? null : id)}
            className={`flex items-center gap-1.5 px-3 py-1 rounded text-sm font-mono whitespace-nowrap transition-colors ${
              isActive ? "bg-accent text-bg" : "bg-surface text-muted hover:text-white hover:bg-surface-hover"
            }`}
            aria-pressed={isActive}
          >
            <span className={`w-2 h-2 rounded-full ${dotColor}`} aria-hidden="true" />
            {label}
            {scanned && p && (p.acc > 0 || p.dis > 0) && (
              <span className="text-xs ml-1">
                <span className="text-bullish">{p.acc}</span>
                /
                <span className="text-bearish">{p.dis}</span>
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
