import { NextResponse } from 'next/server'
import { supabase } from '@/lib/supabase'

export async function POST(request: Request) {
  try {
    const { transition_id, reason } = await request.json()

    if (!transition_id) {
      return NextResponse.json(
        { success: false, error: 'transition_id required' },
        { status: 400 }
      )
    }

    // Cancel transition
    const { error } = await supabase
      .from('trading_exchange_transitions')
      .update({
        status: 'cancelled',
        last_error: reason || 'Cancelled by user',
        completed_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      })
      .eq('id', transition_id)

    if (error) throw error

    // Clear in_transition flags
    await supabase
      .from('trading_positions')
      .update({ in_transition: false })
      .eq('transition_id', transition_id)

    return NextResponse.json({
      success: true,
      message: 'Transition cancelled successfully'
    })
  } catch (error) {
    console.error('Error cancelling transition:', error)
    return NextResponse.json(
      { success: false, error: 'Failed to cancel transition' },
      { status: 500 }
    )
  }
}
