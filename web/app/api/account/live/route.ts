import { NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

// Alpaca API configuration
const ALPACA_API_KEY = process.env.ALPACA_API_KEY
const ALPACA_SECRET_KEY = process.env.ALPACA_SECRET_KEY
const ALPACA_PAPER = process.env.ALPACA_PAPER_TRADING !== 'false'
const ALPACA_BASE_URL = ALPACA_PAPER
  ? 'https://paper-api.alpaca.markets'
  : 'https://api.alpaca.markets'

interface AlpacaAccount {
  id: string
  account_number: string
  status: string
  currency: string
  cash: string
  portfolio_value: string
  buying_power: string
  equity: string
  last_equity: string
  long_market_value: string
  short_market_value: string
  initial_margin: string
  maintenance_margin: string
  daytrade_count: number
  pattern_day_trader: boolean
}

interface AlpacaPosition {
  symbol: string
  qty: string
  avg_entry_price: string
  market_value: string
  cost_basis: string
  unrealized_pl: string
  unrealized_plpc: string
  unrealized_intraday_pl: string
  unrealized_intraday_plpc: string
  current_price: string
  change_today: string
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
    cache: 'no-store',
  })

  if (!response.ok) {
    const error = await response.text()
    throw new Error(`Alpaca API error: ${response.status} - ${error}`)
  }

  return response.json()
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
    cache: 'no-store',
  })

  if (!response.ok) {
    const error = await response.text()
    throw new Error(`Alpaca API error: ${response.status} - ${error}`)
  }

  return response.json()
}

export async function GET() {
  try {
    // Check if Alpaca credentials are available
    if (!ALPACA_API_KEY || !ALPACA_SECRET_KEY) {
      return NextResponse.json({
        success: false,
        configured: false,
        error: 'Alpaca credentials not configured',
      })
    }

    // Fetch account and positions in parallel
    const [account, positions] = await Promise.all([
      fetchAlpacaAccount(),
      fetchAlpacaPositions(),
    ])

    const equity = parseFloat(account.equity)
    const lastEquity = parseFloat(account.last_equity)
    const cash = parseFloat(account.cash)
    const buyingPower = parseFloat(account.buying_power)
    const longMarketValue = parseFloat(account.long_market_value)
    const shortMarketValue = parseFloat(account.short_market_value)

    // Calculate total position value
    const positionsValue = longMarketValue + Math.abs(shortMarketValue)

    // Calculate daily P&L
    const dailyPnl = equity - lastEquity
    const dailyPnlPct = lastEquity > 0 ? (dailyPnl / lastEquity) * 100 : 0

    // Calculate total unrealized P&L from positions
    const totalUnrealizedPnl = positions.reduce(
      (sum, p) => sum + parseFloat(p.unrealized_pl || '0'),
      0
    )

    // Calculate exposure percentage
    const exposurePct = equity > 0 ? (positionsValue / equity) * 100 : 0

    // Build positions summary
    const positionsSummary = positions.map(p => {
      const symbol = p.symbol.includes('/')
        ? p.symbol.split('/')[0]
        : p.symbol.endsWith('USD')
          ? p.symbol.slice(0, -3)
          : p.symbol

      return {
        symbol,
        qty: parseFloat(p.qty),
        entryPrice: parseFloat(p.avg_entry_price),
        currentPrice: parseFloat(p.current_price),
        marketValue: parseFloat(p.market_value),
        unrealizedPnl: parseFloat(p.unrealized_pl),
        unrealizedPnlPct: parseFloat(p.unrealized_plpc) * 100,
        changeToday: parseFloat(p.change_today) * 100,
      }
    })

    return NextResponse.json({
      success: true,
      configured: true,
      timestamp: new Date().toISOString(),
      account: {
        equity,
        cash,
        buyingPower,
        positionsValue,
        lastEquity,
        dailyPnl,
        dailyPnlPct,
        totalUnrealizedPnl,
        exposurePct,
        positionsCount: positions.length,
      },
      positions: positionsSummary,
      mode: ALPACA_PAPER ? 'paper' : 'live',
    })
  } catch (error) {
    console.error('Error fetching live account data:', error)
    return NextResponse.json(
      {
        success: false,
        configured: true,
        error: error instanceof Error ? error.message : 'Failed to fetch account data',
      },
      { status: 500 }
    )
  }
}
