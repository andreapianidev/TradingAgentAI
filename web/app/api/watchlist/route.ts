import { NextRequest, NextResponse } from 'next/server'
import { getSupabase } from '@/lib/supabase'

/**
 * GET /api/watchlist
 * Get all active watchlist entries with opportunity scores
 */
export async function GET(request: NextRequest) {
  try {
    const supabase = getSupabase()
    const { searchParams } = new URL(request.url)
    const tier = searchParams.get('tier') // Optional filter: CORE, OPPORTUNISTIC, SATELLITE

    let query = supabase
      .from('trading_watchlist')
      .select('*')
      .eq('is_active', true)
      .order('opportunity_score', { ascending: false })

    if (tier) {
      query = query.eq('tier', tier)
    }

    const { data, error } = await query

    if (error) {
      console.error('Error fetching watchlist:', error)
      return NextResponse.json(
        { error: 'Failed to fetch watchlist' },
        { status: 500 }
      )
    }

    // Calculate summary stats
    const summary = {
      total_active: data?.length || 0,
      core_count: data?.filter(e => e.tier === 'CORE').length || 0,
      opportunistic_count: data?.filter(e => e.tier === 'OPPORTUNISTIC').length || 0,
      avg_opportunity_score: data && data.length > 0
        ? data.reduce((sum, e) => sum + (e.opportunity_score || 0), 0) / data.length
        : 0,
    }

    return NextResponse.json({
      success: true,
      watchlist: data || [],
      summary,
    })
  } catch (error) {
    console.error('Unexpected error fetching watchlist:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}
