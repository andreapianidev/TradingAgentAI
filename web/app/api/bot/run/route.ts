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
    // This endpoint triggers the Python trading bot
    // The actual execution happens on Railway/external service
    // This just creates a cycle record and potentially triggers via webhook

    const cycleId = crypto.randomUUID()
    const startedAt = new Date().toISOString()

    // Create a new cycle record
    const { error: cycleError } = await supabase.from('trading_cycles').insert({
      id: cycleId,
      started_at: startedAt,
      status: 'running',
      trading_mode: 'paper'
    })

    if (cycleError) throw cycleError

    // If you have a Railway/external webhook URL, trigger it here
    const webhookUrl = process.env.TRADING_BOT_WEBHOOK_URL
    if (webhookUrl) {
      try {
        await fetch(webhookUrl, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ cycle_id: cycleId, trigger: 'manual' })
        })
      } catch (webhookError) {
        console.error('Failed to trigger webhook:', webhookError)
      }
    }

    // Log the manual trigger
    await supabase.from('trading_bot_logs').insert({
      log_level: 'INFO',
      message: 'Manual trading cycle triggered from dashboard',
      component: 'api',
      cycle_id: cycleId,
      trading_mode: 'paper'
    })

    return NextResponse.json({
      success: true,
      cycle_id: cycleId,
      started_at: startedAt,
      message: 'Trading cycle triggered'
    })
  } catch (error) {
    console.error('Error running bot cycle:', error)
    return NextResponse.json(
      { success: false, error: 'Failed to trigger trading cycle' },
      { status: 500 }
    )
  }
}

export async function GET() {
  // Same as POST for convenience (can be called via cron)
  return POST()
}
