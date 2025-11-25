import { NextResponse } from 'next/server'
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
)

export async function GET() {
  try {
    // Get bot active status from settings
    const { data: botActiveSetting } = await supabase
      .from('trading_settings')
      .select('setting_value')
      .eq('setting_key', 'bot_active')
      .single()

    // Get trading mode from settings
    const { data: tradingModeSetting } = await supabase
      .from('trading_settings')
      .select('setting_value')
      .eq('setting_key', 'paper_trading_enabled')
      .single()

    // Get latest portfolio snapshot
    const { data: snapshot } = await supabase
      .from('trading_portfolio_snapshots')
      .select('*')
      .order('timestamp', { ascending: false })
      .limit(1)
      .single()

    // Get unread alerts count
    const { count: unreadAlerts } = await supabase
      .from('trading_alerts')
      .select('*', { count: 'exact', head: true })
      .eq('is_read', false)

    // Get open positions count
    const { count: openPositions } = await supabase
      .from('trading_positions')
      .select('*', { count: 'exact', head: true })
      .eq('status', 'open')

    // Parse bot_active setting
    let botActive = false
    try {
      botActive = JSON.parse(botActiveSetting?.setting_value || 'false')
    } catch {
      botActive = botActiveSetting?.setting_value === 'true'
    }

    // Parse paper_trading_enabled setting
    let paperTradingEnabled = true
    try {
      paperTradingEnabled = JSON.parse(tradingModeSetting?.setting_value || 'true')
    } catch {
      paperTradingEnabled = tradingModeSetting?.setting_value !== 'false'
    }

    return NextResponse.json({
      success: true,
      bot_active: botActive,
      trading_mode: paperTradingEnabled ? 'paper' : 'live',
      unread_alerts: unreadAlerts || 0,
      open_positions: openPositions || 0,
      portfolio: snapshot ? {
        total_equity: snapshot.total_equity_usdc,
        available_balance: snapshot.available_balance_usdc,
        total_pnl: snapshot.total_pnl,
        total_pnl_pct: snapshot.total_pnl_pct,
        exposure_pct: snapshot.exposure_pct,
        last_update: snapshot.timestamp
      } : null
    })
  } catch (error) {
    console.error('Error fetching status:', error)
    return NextResponse.json(
      { success: false, error: 'Failed to fetch status' },
      { status: 500 }
    )
  }
}
