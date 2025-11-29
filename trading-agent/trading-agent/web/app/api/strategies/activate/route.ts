import { NextRequest, NextResponse } from 'next/server'
import { getSupabase } from '@/lib/supabase'

/**
 * POST /api/strategies/activate
 * Activate a trading strategy (sets is_active to true, deactivates all others)
 */
export async function POST(request: NextRequest) {
  try {
    const supabase = getSupabase()
    const body = await request.json()
    const { strategy_id } = body

    if (!strategy_id) {
      return NextResponse.json(
        { error: 'strategy_id is required' },
        { status: 400 }
      )
    }

    // Step 1: Deactivate all strategies
    const { error: deactivateError } = await supabase
      .from('trading_strategies')
      .update({ is_active: false })
      .neq('id', '00000000-0000-0000-0000-000000000000') // Update all rows

    if (deactivateError) {
      console.error('Error deactivating strategies:', deactivateError)
      return NextResponse.json(
        { error: 'Failed to deactivate existing strategies' },
        { status: 500 }
      )
    }

    // Step 2: Activate the selected strategy and increment activation_count
    const { data, error } = await supabase
      .from('trading_strategies')
      .update({
        is_active: true,
        activated_at: new Date().toISOString(),
      })
      .eq('id', strategy_id)
      .select()
      .single()

    if (error) {
      console.error('Error activating strategy:', error)
      return NextResponse.json(
        { error: 'Failed to activate strategy' },
        { status: 500 }
      )
    }

    // Step 3: Increment activation_count
    const { error: incrementError } = await supabase
      .from('trading_strategies')
      .update({
        activation_count: (data?.activation_count || 0) + 1,
      })
      .eq('id', strategy_id)

    if (incrementError) {
      console.warn('Failed to increment activation count:', incrementError)
      // Don't fail the request, just log the warning
    }

    return NextResponse.json({
      success: true,
      strategy: data,
      message: `Strategy "${data?.display_name}" activated successfully`,
    })
  } catch (error) {
    console.error('Unexpected error activating strategy:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}
