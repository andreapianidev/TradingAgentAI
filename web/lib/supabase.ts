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
