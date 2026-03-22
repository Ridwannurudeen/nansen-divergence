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

export interface DeepDiveData {
  chain: string;
  token: string;
  flow_intelligence: Record<string, unknown>;
  who_bought_sold: Record<string, unknown>;
  indicators: Record<string, unknown>;
  wallets: {
    address: string;
    labels: Record<string, unknown>;
    pnl_summary: Record<string, unknown>;
  }[];
}

export interface ChainFlow {
  token_count: number;
  sm_flow_total: number;
  sm_buy_total: number;
  sm_sell_total: number;
  accumulation: number;
  distribution: number;
  high_confidence: number;
  trader_count: number;
  momentum_score: number;
}

export interface SectorFlow {
  token_count: number;
  net_flow: number;
  tokens: string[];
}

export interface FlowsData {
  chains: Record<string, ChainFlow>;
  sectors: Record<string, SectorFlow>;
  timestamp: string | null;
}

export interface SignalOutcome {
  token_address: string;
  token_symbol: string;
  chain: string;
  phase: string;
  confidence: string;
  signal_price: number;
  current_price: number;
  price_change_pct: number;
  days_ago: number;
  divergence_strength: number;
}

export interface OutcomesData {
  outcomes: SignalOutcome[];
  stats: BacktestStats;
}
