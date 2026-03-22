export interface Token {
  chain: string;
  token_address: string;
  token_symbol: string;
  price_usd: number;
  price_change: number;
  market_cap: number;
  volume_24h: number;
  market_netflow: number;
  sm_net_flow: number;
  sm_buy_volume: number;
  sm_sell_volume: number;
  sm_trader_count: number;
  sm_wallet_labels: string[];
  sm_holdings_value: number;
  sm_holdings_change: number;
  divergence_strength: number;
  alpha_score: number;
  phase: "ACCUMULATION" | "DISTRIBUTION" | "MARKUP" | "MARKDOWN";
  confidence: "HIGH" | "MEDIUM" | "LOW";
  narrative: string;
  has_sm_data: boolean;
  is_new?: boolean;
}

export interface RadarToken {
  chain: string;
  token_address: string;
  token_symbol: string;
  sm_net_flow_24h: number;
  sm_net_flow_7d: number;
  sm_trader_count: number;
  sm_sectors: string[];
  market_cap: number;
}

export interface ScanSummary {
  total_tokens: number;
  with_sm_data: number;
  sm_data_pct: number;
  divergence_signals: number;
  accumulation: number;
  distribution: number;
  confidence_high: number;
  confidence_medium: number;
  confidence_low: number;
}

export interface BacktestStats {
  total_signals: number;
  wins: number;
  losses: number;
  win_rate: number;
  avg_return: number;
  best_return: number;
  worst_return: number;
}

export interface ScanData {
  results: Token[];
  radar: RadarToken[];
  summary: ScanSummary;
  chains: string[];
  timestamp: string;
  backtest: BacktestStats;
}
