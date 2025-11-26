import { NextResponse } from 'next/server'
import { createClient } from '@supabase/supabase-js'

// Alpaca API configuration
const ALPACA_API_KEY = process.env.ALPACA_API_KEY
const ALPACA_SECRET_KEY = process.env.ALPACA_SECRET_KEY
const ALPACA_PAPER = process.env.ALPACA_PAPER_TRADING !== 'false'
const ALPACA_BASE_URL = ALPACA_PAPER
  ? 'https://paper-api.alpaca.markets'
  : 'https://api.alpaca.markets'

function getSupabaseClient() {
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
  const supabaseKey = process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY

  if (!supabaseUrl || !supabaseKey) {
    throw new Error('Missing Supabase environment variables')
  }

  return createClient(supabaseUrl, supabaseKey)
}

interface AlpacaPosition {
  asset_id: string
  symbol: string
  exchange: string
  asset_class: string
  qty: string
  avg_entry_price: string
  side: string
  market_value: string
  cost_basis: string
  unrealized_pl: string
  unrealized_plpc: string
  unrealized_intraday_pl: string
  unrealized_intraday_plpc: string
  current_price: string
  lastday_price: string
  change_today: string
}

interface AlpacaAccount {
  id: string
  account_number: string
  status: string
  currency: string
  cash: string
  portfolio_value: string
  buying_power: string
  equity: string
}

async function fetchAlpacaPositions(): Promise<AlpacaPosition[]> {
  if (!ALPACA_API_KEY || !ALPACA_SECRET_KEY) {
    throw new Error('Missing Alpaca API credentials')
  }

  const response = await fetch(`${ALPACA_BASE_URL}/v2/positions`, {
    headers: {
      'APCA-API-KEY-ID': ALPACA_API_KEY,
      'APCA-API-SECRET-KEY': ALPACA_SECRET_KEY,
    },
  })

  if (!response.ok) {
    const error = await response.text()
    throw new Error(`Alpaca API error: ${response.status} - ${error}`)
  }

  return response.json()
}

async function fetchAlpacaAccount(): Promise<AlpacaAccount> {
  if (!ALPACA_API_KEY || !ALPACA_SECRET_KEY) {
    throw new Error('Missing Alpaca API credentials')
  }

  const response = await fetch(`${ALPACA_BASE_URL}/v2/account`, {
    headers: {
      'APCA-API-KEY-ID': ALPACA_API_KEY,
      'APCA-API-SECRET-KEY': ALPACA_SECRET_KEY,
    },
  })

  if (!response.ok) {
    const error = await response.text()
    throw new Error(`Alpaca API error: ${response.status} - ${error}`)
  }

  return response.json()
}

export async function POST() {
  try {
    const supabase = getSupabaseClient()

    // Fetch positions from Alpaca
    const [alpacaPositions, alpacaAccount] = await Promise.all([
      fetchAlpacaPositions(),
      fetchAlpacaAccount(),
    ])

    console.log(`Syncing ${alpacaPositions.length} positions from Alpaca`)

    // Get existing open positions from database
    const { data: dbPositions, error: fetchError } = await supabase
      .from('trading_positions')
      .select('*')
      .eq('status', 'open')

    if (fetchError) throw fetchError

    const dbPositionMap = new Map(
      (dbPositions || []).map(p => [p.symbol, p])
    )

    const results = {
      created: [] as string[],
      updated: [] as string[],
      closed: [] as string[],
    }

    const now = new Date().toISOString()
    const tradingMode = ALPACA_PAPER ? 'paper' : 'live'

    // Process Alpaca positions
    for (const pos of alpacaPositions) {
      // Extract base symbol (remove /USD or USD suffix for crypto)
      let symbol = pos.symbol
      if (symbol.includes('/')) {
        symbol = symbol.split('/')[0]
      } else if (symbol.endsWith('USD')) {
        symbol = symbol.slice(0, -3)
      }

      const qty = parseFloat(pos.qty)
      const direction = qty > 0 ? 'long' : 'short'
      const entryPrice = parseFloat(pos.avg_entry_price)
      const currentPrice = parseFloat(pos.current_price)
      const unrealizedPnl = parseFloat(pos.unrealized_pl)
      const unrealizedPnlPct = parseFloat(pos.unrealized_plpc) * 100

      const existingPosition = dbPositionMap.get(symbol)

      if (existingPosition) {
        // Update existing position
        const { error: updateError } = await supabase
          .from('trading_positions')
          .update({
            quantity: Math.abs(qty),
            entry_price: entryPrice,
            unrealized_pnl: unrealizedPnl,
            unrealized_pnl_pct: unrealizedPnlPct,
            updated_at: now,
          })
          .eq('id', existingPosition.id)

        if (updateError) {
          console.error(`Failed to update position ${symbol}:`, updateError)
        } else {
          results.updated.push(symbol)
        }

        // Remove from map so we know it's been processed
        dbPositionMap.delete(symbol)
      } else {
        // Create new position
        const { error: insertError } = await supabase
          .from('trading_positions')
          .insert({
            symbol,
            direction,
            entry_timestamp: now,
            entry_price: entryPrice,
            quantity: Math.abs(qty),
            leverage: 1,
            unrealized_pnl: unrealizedPnl,
            unrealized_pnl_pct: unrealizedPnlPct,
            status: 'open',
            trading_mode: tradingMode,
            created_at: now,
            updated_at: now,
          })

        if (insertError) {
          console.error(`Failed to create position ${symbol}:`, insertError)
        } else {
          results.created.push(symbol)
        }
      }
    }

    // Close positions that exist in DB but not in Alpaca
    for (const [symbol, position] of dbPositionMap) {
      const { error: closeError } = await supabase
        .from('trading_positions')
        .update({
          status: 'closed',
          exit_timestamp: now,
          exit_reason: 'sync_not_found',
          updated_at: now,
        })
        .eq('id', position.id)

      if (closeError) {
        console.error(`Failed to close position ${symbol}:`, closeError)
      } else {
        results.closed.push(symbol)
      }
    }

    // Update portfolio snapshot
    const totalEquity = parseFloat(alpacaAccount.equity)
    const availableBalance = parseFloat(alpacaAccount.buying_power)
    const marginUsed = totalEquity - availableBalance

    // Calculate total unrealized PnL
    const totalUnrealizedPnl = alpacaPositions.reduce(
      (sum, p) => sum + parseFloat(p.unrealized_pl),
      0
    )

    // Calculate exposure
    const totalPositionValue = alpacaPositions.reduce(
      (sum, p) => sum + Math.abs(parseFloat(p.market_value)),
      0
    )
    const exposurePct = totalEquity > 0 ? (totalPositionValue / totalEquity) * 100 : 0

    // Create portfolio snapshot
    await supabase.from('trading_portfolio_snapshots').insert({
      timestamp: now,
      total_equity_usdc: totalEquity,
      available_balance_usdc: availableBalance,
      margin_used_usdc: marginUsed,
      open_positions_count: alpacaPositions.length,
      exposure_pct: exposurePct,
      total_pnl: totalUnrealizedPnl,
      total_pnl_pct: totalEquity > 0 ? (totalUnrealizedPnl / totalEquity) * 100 : 0,
      daily_pnl: totalUnrealizedPnl,
      daily_pnl_pct: totalEquity > 0 ? (totalUnrealizedPnl / totalEquity) * 100 : 0,
      trading_mode: tradingMode,
    })

    return NextResponse.json({
      success: true,
      message: `Synced ${alpacaPositions.length} positions from Alpaca`,
      results,
      account: {
        equity: totalEquity,
        buying_power: availableBalance,
        positions: alpacaPositions.length,
      },
    })
  } catch (error) {
    console.error('Error syncing positions:', error)
    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to sync positions'
      },
      { status: 500 }
    )
  }
}

export async function GET() {
  // Also support GET requests for easy testing
  return POST()
}
