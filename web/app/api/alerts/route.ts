import { NextRequest, NextResponse } from 'next/server'
import { getSupabase } from '@/lib/supabase'

/**
 * GET /api/alerts
 * Get recent trading alerts (watchlist changes, system events, etc.)
 */
export async function GET(request: NextRequest) {
  try {
    const supabase = getSupabase()
    const { searchParams } = new URL(request.url)
    const limit = parseInt(searchParams.get('limit') || '20')
    const type = searchParams.get('type') // Optional filter: WATCHLIST_ADDED, WATCHLIST_REMOVED, etc.

    let query = supabase
      .from('trading_alerts')
      .select('*')
      .order('created_at', { ascending: false })
      .limit(limit)

    if (type) {
      query = query.eq('alert_type', type)
    }

    const { data, error } = await query

    if (error) {
      console.error('Error fetching alerts:', error)
      return NextResponse.json(
        { error: 'Failed to fetch alerts' },
        { status: 500 }
      )
    }

    // Count by type for summary
    const watchlistAlerts = data?.filter(a => a.alert_type?.startsWith('WATCHLIST_')) || []

    return NextResponse.json({
      success: true,
      alerts: data || [],
      summary: {
        total: data?.length || 0,
        watchlist_count: watchlistAlerts.length,
      },
    })
  } catch (error) {
    console.error('Unexpected error fetching alerts:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}
