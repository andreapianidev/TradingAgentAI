import { NextResponse } from 'next/server'
import { createClient } from '@supabase/supabase-js'

export const dynamic = 'force-dynamic'

function getSupabaseClient() {
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
  const supabaseKey = process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY

  if (!supabaseUrl || !supabaseKey) {
    throw new Error('Missing Supabase environment variables')
  }

  return createClient(supabaseUrl, supabaseKey)
}

export async function GET() {
  try {
    const supabase = getSupabaseClient()
    // Check if bot process is running
    const isRunning = global.botProcess && !global.botProcess.killed

    // Get latest portfolio snapshot
    const { data: snapshot } = await supabase
      .from('trading_portfolio_snapshots')
      .select('*')
      .order('timestamp', { ascending: false })
      .limit(1)
      .single()

    // Get open positions count
    const { count: openPositions } = await supabase
      .from('trading_positions')
      .select('*', { count: 'exact', head: true })
      .eq('status', 'open')

    // Get latest cycle info if bot is running
    let currentCycle = null
    if (global.botCycleId) {
      const { data: cycle } = await supabase
        .from('trading_cycles')
        .select('*')
        .eq('id', global.botCycleId)
        .single()
      currentCycle = cycle
    }

    // Get the current symbol being analyzed (from latest log)
    let currentSymbol = null
    if (isRunning) {
      const { data: latestLog } = await supabase
        .from('trading_bot_logs')
        .select('symbol')
        .not('symbol', 'is', null)
        .order('created_at', { ascending: false })
        .limit(1)
        .single()
      currentSymbol = latestLog?.symbol
    }

    return NextResponse.json({
      isRunning: !!isRunning,
      cycleId: global.botCycleId,
      startedAt: global.botStartedAt,
      currentSymbol,
      currentCycle,
      portfolio: snapshot ? {
        equity: snapshot.total_equity_usdc || 0,
        available: snapshot.available_balance_usdc || 0,
        exposure: snapshot.exposure_pct || 0,
        positions: openPositions || 0
      } : null
    })
  } catch (error) {
    console.error('Error fetching bot status:', error)
    return NextResponse.json(
      {
        isRunning: false,
        error: 'Failed to fetch bot status'
      },
      { status: 500 }
    )
  }
}
