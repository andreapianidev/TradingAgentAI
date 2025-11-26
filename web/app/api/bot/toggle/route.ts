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
    const { active } = await request.json()

    // Update bot_active setting
    const { error } = await supabase
      .from('trading_settings')
      .update({
        setting_value: JSON.stringify(active),
        updated_at: new Date().toISOString()
      })
      .eq('setting_key', 'bot_active')

    if (error) throw error

    // Create an alert for the status change
    await supabase.from('trading_alerts').insert({
      alert_type: active ? 'bot_started' : 'bot_stopped',
      severity: 'info',
      title: active ? 'Bot Started' : 'Bot Stopped',
      message: active
        ? 'Trading bot has been activated and will start trading on the next cycle.'
        : 'Trading bot has been deactivated. No new trades will be executed.',
      trading_mode: 'paper'
    })

    return NextResponse.json({
      success: true,
      active,
      message: active ? 'Bot activated' : 'Bot deactivated'
    })
  } catch (error) {
    console.error('Error toggling bot:', error)
    return NextResponse.json(
      { success: false, error: 'Failed to toggle bot status' },
      { status: 500 }
    )
  }
}
