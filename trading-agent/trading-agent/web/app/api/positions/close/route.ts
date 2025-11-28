import { NextResponse } from 'next/server'
import { createClient } from '@supabase/supabase-js'

function getSupabaseClient() {
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
  const supabaseKey = process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY

  if (!supabaseUrl || !supabaseKey) {
    throw new Error('Missing Supabase environment variables')
  }

  return createClient(supabaseUrl, supabaseKey)
}

export async function POST(request: Request) {
  try {
    const supabase = getSupabaseClient()
    const { position_id } = await request.json()

    if (!position_id) {
      return NextResponse.json(
        { success: false, error: 'Position ID is required' },
        { status: 400 }
      )
    }

    // Get the position
    const { data: position, error: fetchError } = await supabase
      .from('trading_positions')
      .select('*')
      .eq('id', position_id)
      .eq('status', 'open')
      .single()

    if (fetchError || !position) {
      return NextResponse.json(
        { success: false, error: 'Position not found or already closed' },
        { status: 404 }
      )
    }

    // For paper trading, we simulate the close
    // In live trading, this would call the exchange API
    const exitTimestamp = new Date().toISOString()

    // For demo purposes, we'll use the current unrealized P&L as realized
    // In production, this would fetch real market price
    const realizedPnl = parseFloat(position.unrealized_pnl || '0')
    const realizedPnlPct = parseFloat(position.unrealized_pnl_pct || '0')

    // Create a close decision record
    const { data: decision, error: decisionError } = await supabase
      .from('trading_decisions')
      .insert({
        symbol: position.symbol,
        timestamp: exitTimestamp,
        action: 'close',
        direction: position.direction,
        confidence: 1.0,
        reasoning: 'Manual close from dashboard',
        execution_status: 'executed',
        execution_timestamp: exitTimestamp,
        entry_price: position.entry_price,
        entry_quantity: position.quantity,
        trading_mode: position.trading_mode
      })
      .select()
      .single()

    if (decisionError) throw decisionError

    // Update the position
    const { error: updateError } = await supabase
      .from('trading_positions')
      .update({
        status: 'closed',
        exit_timestamp: exitTimestamp,
        exit_price: position.entry_price, // In real scenario, would be current market price
        exit_reason: 'manual',
        exit_trade_id: decision.id,
        realized_pnl: realizedPnl,
        realized_pnl_pct: realizedPnlPct,
        updated_at: exitTimestamp
      })
      .eq('id', position_id)

    if (updateError) throw updateError

    // Create an alert
    await supabase.from('trading_alerts').insert({
      alert_type: 'position_closed',
      severity: 'info',
      symbol: position.symbol,
      position_id: position_id,
      decision_id: decision.id,
      title: `Position Closed: ${position.symbol}`,
      message: `Manually closed ${position.direction.toUpperCase()} position on ${position.symbol}. P&L: $${realizedPnl.toFixed(2)} (${realizedPnlPct.toFixed(2)}%)`,
      trading_mode: position.trading_mode
    })

    // Log the action
    await supabase.from('trading_bot_logs').insert({
      log_level: 'INFO',
      message: `Position ${position_id} closed manually`,
      component: 'api',
      symbol: position.symbol,
      details: { position_id, realized_pnl: realizedPnl },
      trading_mode: position.trading_mode
    })

    return NextResponse.json({
      success: true,
      position_id,
      realized_pnl: realizedPnl,
      realized_pnl_pct: realizedPnlPct,
      message: 'Position closed successfully'
    })
  } catch (error) {
    console.error('Error closing position:', error)
    return NextResponse.json(
      { success: false, error: 'Failed to close position' },
      { status: 500 }
    )
  }
}
