import { createClient, SupabaseClient } from '@supabase/supabase-js'

let supabaseInstance: SupabaseClient | null = null

export function getSupabase(): SupabaseClient {
  if (!supabaseInstance) {
    const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
    const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY

    if (!supabaseUrl || !supabaseAnonKey) {
      throw new Error('Missing Supabase environment variables')
    }

    supabaseInstance = createClient(supabaseUrl, supabaseAnonKey)
  }
  return supabaseInstance
}

// Legacy export - prefer using getSupabase() for lazy initialization
export const supabase = new Proxy({} as SupabaseClient, {
  get(_, prop) {
    return (getSupabase() as any)[prop]
  }
})

// Types for trading tables
export interface TradingPosition {
  id: string
  created_at: string
  updated_at: string
  symbol: string
  direction: 'long' | 'short'
  entry_timestamp: string
  entry_price: number
  quantity: number
  leverage: number
  exit_timestamp?: string
  exit_price?: number
  exit_reason?: string
  realized_pnl?: number
  realized_pnl_pct?: number
  unrealized_pnl?: number
  unrealized_pnl_pct?: number
  stop_loss_price?: number
  take_profit_price?: number
  liquidation_price?: number
  status: 'open' | 'closed'
  trading_mode: 'paper' | 'live'
}

export interface TradingDecision {
  id: string
  created_at: string
  context_id?: string
  symbol: string
  timestamp: string
  action: 'open' | 'close' | 'hold'
  direction?: 'long' | 'short'
  leverage?: number
  position_size_pct?: number
  stop_loss_pct?: number
  take_profit_pct?: number
  confidence?: number
  reasoning?: string
  execution_status: 'pending' | 'executed' | 'failed' | 'skipped'
  execution_details?: any
  execution_timestamp?: string
  entry_price?: number
  entry_quantity?: number
  order_id?: string
  trading_mode: 'paper' | 'live'
}

export interface TradingMarketContext {
  id: string
  created_at: string
  symbol: string
  timeframe: string
  timestamp: string
  price: number
  price_change_24h?: number
  macd?: number
  macd_signal?: number
  macd_histogram?: number
  rsi?: number
  ema2?: number
  ema20?: number
  pivot_pp?: number
  pivot_r1?: number
  pivot_r2?: number
  pivot_s1?: number
  pivot_s2?: number
  pivot_distance_pct?: number
  forecast_trend?: string
  forecast_target_price?: number
  forecast_change_pct?: number
  forecast_confidence?: number
  orderbook_bid_volume?: number
  orderbook_ask_volume?: number
  orderbook_ratio?: number
  sentiment_label?: string
  sentiment_score?: number
  raw_data?: any
}

export interface TradingPortfolioSnapshot {
  id: string
  created_at: string
  timestamp: string
  total_equity_usdc: number
  available_balance_usdc: number
  margin_used_usdc: number
  open_positions_count: number
  exposure_pct: number
  total_pnl: number
  total_pnl_pct: number
  daily_pnl: number
  daily_pnl_pct: number
  max_drawdown: number
  max_drawdown_pct: number
  total_trades: number
  winning_trades: number
  losing_trades: number
  win_rate: number
  raw_data?: any
  trading_mode: 'paper' | 'live'
}

export interface TradingAlert {
  id: string
  created_at: string
  alert_type: string
  severity: 'info' | 'warning' | 'critical'
  symbol?: string
  position_id?: string
  decision_id?: string
  title: string
  message: string
  details?: any
  is_read: boolean
  read_at?: string
  is_dismissed: boolean
  trading_mode: 'paper' | 'live'
}

export interface TradingSetting {
  id: string
  created_at: string
  updated_at: string
  setting_key: string
  setting_value: any
  description?: string
  category: string
}

export interface TradingStrategy {
  id: string
  created_at: string
  updated_at: string
  name: string
  display_name: string
  description?: string
  is_active: boolean
  is_default: boolean
  config: {
    max_position_size_pct: number
    max_total_exposure_pct: number
    tp_range_min: number
    tp_range_max: number
    auto_close_at_profit_pct?: number | null
    sl_range_min: number
    sl_range_max: number
    min_confidence: number
  }
  activated_at?: string
  activation_count: number
}

export interface TradingCycle {
  id: string
  created_at: string
  started_at: string
  completed_at?: string
  duration_seconds?: number
  status: 'running' | 'completed' | 'failed'
  results?: any
  symbols_processed: number
  decisions_made: number
  orders_executed: number
  errors_count: number
  error_message?: string
  error_stack?: string
  trading_mode: 'paper' | 'live'
}

export interface TradingNews {
  id: string
  created_at: string
  title: string
  summary?: string
  url?: string
  source?: string
  published_at?: string
  sentiment: 'positive' | 'negative' | 'neutral'
  symbols?: string[]
  raw_data?: any
}

export interface TradingWhaleAlert {
  id: string
  created_at: string
  blockchain?: string
  symbol: string
  amount?: number
  amount_usd?: number
  from_address?: string
  from_type?: string
  to_address?: string
  to_type?: string
  tx_hash?: string
  transaction_time?: string
  flow_direction?: string
  raw_data?: any
}

export interface TradingWhaleFlowSummary {
  id: string
  created_at: string
  period_start?: string
  period_end?: string
  symbol?: string
  inflow_exchange: number
  outflow_exchange: number
  net_flow: number
  alert_count: number
  interpretation?: string
}

export interface TradingAIAnalysis {
  id: string
  created_at: string
  analysis_date: string
  symbol: string
  summary_text: string
  market_outlook: 'bullish' | 'bearish' | 'neutral' | 'volatile'
  confidence_score: number
  key_levels?: {
    resistance_1?: number
    resistance_2?: number
    support_1?: number
    support_2?: number
  }
  risk_factors?: string[]
  opportunities?: string[]
  trend_strength?: 'strong' | 'moderate' | 'weak'
  momentum?: 'increasing' | 'decreasing' | 'stable'
  volatility_level?: 'high' | 'medium' | 'low'
  indicators_snapshot?: any
  news_sentiment_summary?: {
    total: number
    positive: number
    negative: number
    sentiment_score: number
    sentiment_label: string
  }
  trading_mode: 'paper' | 'live'
}

export interface TradingCost {
  id: string
  created_at: string
  cost_type: 'llm' | 'trading_fee'
  llm_provider?: string
  llm_model?: string
  input_tokens?: number
  output_tokens?: number
  cached_tokens?: number
  position_id?: string
  fee_type?: string
  trade_value_usd?: number
  fee_rate?: number
  cost_usd: number
  symbol?: string
  decision_id?: string
  trading_mode: 'paper' | 'live'
  details?: any
}

export interface TradingCostSummary {
  id: string
  created_at: string
  period_type: 'daily' | 'monthly'
  period_start: string
  period_end: string
  llm_total_cost_usd: number
  llm_input_tokens: number
  llm_output_tokens: number
  llm_cached_tokens: number
  llm_calls_count: number
  trading_fees_total_usd: number
  trades_count: number
  total_cost_usd: number
  cost_by_symbol?: Record<string, { llm: number; fees: number }>
  trading_mode: 'paper' | 'live'
}

export interface TradingMarketGlobal {
  id: string
  created_at: string
  timestamp: string
  btc_dominance?: number
  eth_dominance?: number
  total_market_cap_usd?: number
  total_volume_24h_usd?: number
  market_cap_change_24h_pct?: number
  active_cryptocurrencies?: number
  trending_coins?: any
  trending_symbols?: string[]
  tracked_trending?: string[]
}

export interface TradingDailyStats {
  id: string
  created_at: string
  date: string
  total_trades: number
  winning_trades: number
  losing_trades: number
  daily_pnl: number
  daily_pnl_pct: number
  total_volume_usdc: number
  starting_equity?: number
  ending_equity?: number
  stats_by_symbol?: any
  trading_mode: 'paper' | 'live'
}

export interface TradingDrawdownTracking {
  id: string
  created_at: string
  date: string
  starting_equity?: number
  current_equity?: number
  daily_pnl?: number
  daily_drawdown_pct?: number
  weekly_drawdown_pct?: number
  trading_halted: boolean
  halt_reason?: string
  trading_mode: 'paper' | 'live'
}

export interface TradingForecastPerformance {
  id: string
  created_at: string
  symbol: string
  forecast_horizon: string
  predicted_price?: number
  actual_price?: number
  prediction_timestamp?: string
  evaluation_timestamp?: string
  mape?: number
  direction_correct?: boolean
  hyperparameters?: any
  trading_mode: 'paper' | 'live'
}

export interface TradingBotLog {
  id: string
  created_at: string
  log_level: 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL'
  message: string
  component?: string
  symbol?: string
  cycle_id?: string
  details?: any
  error_stack?: string
  trading_mode: 'paper' | 'live'
}
