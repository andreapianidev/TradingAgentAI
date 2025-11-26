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

export async function POST() {
  try {
    const supabase = getSupabaseClient()
    // Check if bot is running
    if (!global.botProcess || global.botProcess.killed) {
      return NextResponse.json({
        success: false,
        error: 'Bot is not running',
        isRunning: false
      }, { status: 400 })
    }

    const cycleId = global.botCycleId

    // Log bot stop request
    await supabase.from('trading_bot_logs').insert({
      log_level: 'WARNING',
      message: 'Trading bot stop requested from dashboard',
      component: 'BotController',
      cycle_id: cycleId,
      trading_mode: 'paper'
    })

    // Kill the bot process
    global.botProcess.kill('SIGTERM')

    // Give it a moment to clean up, then force kill if necessary
    setTimeout(() => {
      if (global.botProcess && !global.botProcess.killed) {
        global.botProcess.kill('SIGKILL')
      }
    }, 5000)

    // Update cycle status
    if (cycleId) {
      await supabase
        .from('trading_cycles')
        .update({
          completed_at: new Date().toISOString(),
          status: 'stopped'
        })
        .eq('id', cycleId)
    }

    // Log bot stopped
    await supabase.from('trading_bot_logs').insert({
      log_level: 'INFO',
      message: 'Trading bot stopped by user',
      component: 'BotController',
      cycle_id: cycleId,
      trading_mode: 'paper'
    })

    global.botProcess = null
    global.botCycleId = null
    global.botStartedAt = null

    return NextResponse.json({
      success: true,
      isRunning: false,
      message: 'Trading bot stopped successfully'
    })
  } catch (error) {
    console.error('Error stopping bot:', error)
    return NextResponse.json(
      { success: false, error: 'Failed to stop trading bot' },
      { status: 500 }
    )
  }
}
