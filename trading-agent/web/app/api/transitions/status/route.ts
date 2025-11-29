import { NextResponse } from 'next/server'
import { supabase } from '@/lib/supabase'

export async function GET() {
  try {
    // Get active transition
    const { data: transition, error: transError } = await supabase
      .from('trading_exchange_transitions')
      .select('*')
      .in('status', ['pending', 'in_progress'])
      .order('created_at', { ascending: false })
      .limit(1)
      .maybeSingle()

    if (transError) throw transError

    if (!transition) {
      return NextResponse.json({
        success: true,
        transition: null,
        positions: []
      })
    }

    // Get positions
    const { data: positions, error: posError } = await supabase
      .from('trading_positions')
      .select('*')
      .eq('transition_id', transition.id)
      .eq('status', 'open')

    if (posError) throw posError

    return NextResponse.json({
      success: true,
      transition,
      positions: positions || []
    })
  } catch (error) {
    console.error('Error fetching transition status:', error)
    return NextResponse.json(
      { success: false, error: 'Failed to fetch transition status' },
      { status: 500 }
    )
  }
}
