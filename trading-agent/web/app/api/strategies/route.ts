import { NextRequest, NextResponse } from 'next/server'
import { getSupabase } from '@/lib/supabase'
import type { TradingStrategy } from '@/lib/supabase'

/**
 * GET /api/strategies
 * Fetch all trading strategies from database
 */
export async function GET(_request: NextRequest) {
  try {
    const supabase = getSupabase()

    const { data, error } = await supabase
      .from('trading_strategies')
      .select('*')
      .order('name', { ascending: true })

    if (error) {
      console.error('Error fetching strategies:', error)
      return NextResponse.json(
        { error: 'Failed to fetch strategies' },
        { status: 500 }
      )
    }

    const strategies = (data || []) as TradingStrategy[]

    return NextResponse.json({
      success: true,
      strategies,
      count: strategies.length,
    })
  } catch (error) {
    console.error('Unexpected error fetching strategies:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}
