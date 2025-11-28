import { NextResponse } from 'next/server'
import { supabase } from '@/lib/supabase'

export async function POST(request: Request) {
  try {
    const { transition_id } = await request.json()

    if (!transition_id) {
      return NextResponse.json(
        { success: false, error: 'transition_id required' },
        { status: 400 }
      )
    }

    // Update transition to approved
    const { error } = await supabase
      .from('trading_exchange_transitions')
      .update({
        manual_override_approved: true,
        manual_override_at: new Date().toISOString(),
        manual_override_by: 'dashboard_user',
        updated_at: new Date().toISOString()
      })
      .eq('id', transition_id)

    if (error) throw error

    return NextResponse.json({
      success: true,
      message: 'Transition approved. The bot will close positions on the next cycle.'
    })
  } catch (error) {
    console.error('Error approving transition:', error)
    return NextResponse.json(
      { success: false, error: 'Failed to approve transition' },
      { status: 500 }
    )
  }
}
