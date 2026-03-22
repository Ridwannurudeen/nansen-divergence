export const DEXSCREENER_SLUGS: Record<string, string> = {
  ethereum: "ethereum",
  bnb: "bsc",
  solana: "solana",
  base: "base",
  arbitrum: "arbitrum",
  polygon: "polygon",
  optimism: "optimism",
  avalanche: "avalanche",
  linea: "linea",
};

export function fmtUsd(val: number): string {
  const sign = val > 0 ? "+" : val < 0 ? "-" : "";
  const abs = Math.abs(val);
  if (abs >= 1e9) return `${sign}$${(abs / 1e9).toFixed(1)}B`;
  if (abs >= 1e6) return `${sign}$${(abs / 1e6).toFixed(1)}M`;
  if (abs >= 1e3) return `${sign}$${(abs / 1e3).toFixed(1)}K`;
  if (abs >= 1) return `${sign}$${abs.toFixed(0)}`;
  return `${sign}$${abs.toFixed(2)}`;
}

export function fmtPct(val: number): string {
  const pct = val * 100;
  return `${pct > 0 ? "+" : ""}${pct.toFixed(1)}%`;
}

export function fmtPrice(val: number): string {
  if (val >= 1000) return `$${val.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
  if (val >= 1) return `$${val.toFixed(2)}`;
  if (val >= 0.01) return `$${val.toFixed(4)}`;
  return `$${val.toFixed(6)}`;
}

export function chainLabel(chain: string): string {
  const labels: Record<string, string> = {
    ethereum: "ETH",
    bnb: "BNB",
    solana: "SOL",
    base: "BASE",
    arbitrum: "ARB",
    polygon: "POL",
    optimism: "OP",
    avalanche: "AVAX",
    linea: "LNA",
  };
  return labels[chain] || chain.toUpperCase().slice(0, 4);
}

export function cn(...classes: (string | false | undefined | null)[]): string {
  return classes.filter(Boolean).join(" ");
}
